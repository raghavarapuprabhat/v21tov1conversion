"""F13 — comment retention across Excel re-upload (LLD §8.4, §9.1).

Uses synthetic AnalysisResults so gap_ids are controlled, exercising the two
retention scenarios precisely:
  A) the same gap re-appears (stable id) -> comment re-attaches by gap_id
  B) a gap is resolved/replaced -> its thread is retained for the IS and surfaces
     as "earlier discussion" on that IS's current gap.
"""
from app.domain.linkage import LinkIndex
from app.domain.tree import TreeNode
from app.gaps.registry import summarize
from app.models.collab import Comment
from app.models.gap import Gap, GapType, Severity
from app.repositories.memory import InMemoryRepository
from app.services.analysis import AnalysisResult
from app.services.comments import build_conversation


def _result(gaps: list[Gap]) -> AnalysisResult:
    return AnalysisResult(idx=LinkIndex(), gaps=gaps, tree=TreeNode(name="(root)"),
                          summary=summarize(gaps))


def _gap(gap_id: str, gtype: GapType, is_number: str) -> Gap:
    return Gap(gap_id=gap_id, gap_type=gtype, is_number=is_number,
               detail="x", severity=Severity.HIGH)


def test_scenario_a_same_gap_reupload_keeps_comment(tmp_path):
    repo = InMemoryRepository(str(tmp_path / "s.sqlite"))
    gA = _gap("A1", GapType.G3_DATATYPE, "ISX")
    repo.load([], [], _result([gA]))
    repo.add_comment(Comment(gap_id="A1", author="u", body="discuss this"))

    # Re-upload the same content (row may have moved; gap_id is position-independent)
    summary = repo.load([], [], _result([_gap("A1", GapType.G3_DATATYPE, "ISX")]))
    assert summary.unchanged == 1 and summary.resolved_retained == 0
    kept = repo.list_comments("A1")
    assert len(kept) == 1 and kept[0].body == "discuss this"
    repo.close()


def test_scenario_b_resolved_gap_retained_for_is(tmp_path):
    repo = InMemoryRepository(str(tmp_path / "s.sqlite"))
    repo.load([], [], _result([_gap("A1", GapType.G3_DATATYPE, "ISX")]))
    repo.add_comment(Comment(gap_id="A1", author="u", body="raised on type gap"))

    # Re-upload where the type gap is gone, but the SAME IS now has a different gap
    summary = repo.load([], [], _result([_gap("B1", GapType.G2_OCCURRENCE, "ISX")]))
    assert summary.new == 1 and summary.resolved_retained == 1
    assert summary.comments_retained == 1            # never dropped

    exact, earlier = repo.conversation_parts("B1")
    assert exact == []                               # nothing posted on B1 yet
    assert len(earlier) == 1 and earlier[0].body == "raised on type gap"
    assert earlier[0].is_anchor == "ISX"

    conv = build_conversation(repo, "B1")
    assert conv.thread == []
    assert len(conv.earlier_for_is) == 1
    repo.close()


def test_comments_retained_is_monotonic(tmp_path):
    repo = InMemoryRepository(str(tmp_path / "s.sqlite"))
    repo.load([], [], _result([_gap("A1", GapType.G3_DATATYPE, "ISX")]))
    repo.add_comment(Comment(gap_id="A1", author="u", body="one"))
    repo.add_comment(Comment(gap_id="A1", author="u", body="two"))
    s1 = repo.load([], [], _result([]))              # everything resolved
    s2 = repo.load([], [], _result([]))
    assert s1.comments_retained == 2
    assert s2.comments_retained == 2                 # monotonic, never decreases
    repo.close()


def test_threaded_replies_assemble(tmp_path):
    repo = InMemoryRepository(str(tmp_path / "s.sqlite"))
    repo.load([], [], _result([_gap("A1", GapType.G3_DATATYPE, "ISX")]))
    c1 = repo.add_comment(Comment(gap_id="A1", author="alice", body="root"))
    repo.add_comment(Comment(gap_id="A1", parent_comment_id=c1.comment_id,
                             author="bob", body="reply"))
    conv = build_conversation(repo, "A1")
    assert len(conv.thread) == 1
    assert conv.thread[0].body == "root"
    assert len(conv.thread[0].replies) == 1
    assert conv.thread[0].replies[0].body == "reply"
    repo.close()
