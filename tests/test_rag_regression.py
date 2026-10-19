"""reports/results.json(이번 평가 결과)을 baselines/baseline.json(승인한 기준선)과 비교하는 RAG 회귀 테스트입니다.
하나라도 실패하면 종료 코드 1이 되어 CI 검사가 실패합니다.
    평가 완전성: test_same_cases, test_no_scoring_errors
    절대 하한: test_metric_floor
    허용 하락폭: test_metric_drop
    사례별 회귀: test_stable_case_still_passes
"""
import json
from pathlib import Path

import pytest

# 이번 평가 결과(report)와 승인한 기준선(baseline)을 읽습니다.
ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / "reports" / "results.json").read_text(encoding="utf-8"))
baseline = json.loads((ROOT / "baselines" / "baseline.json").read_text(encoding="utf-8"))

# 이번 평가 범위(smoke 또는 full)의 기준값과, 판정할 채점 함수 이름 목록
split = baseline["splits"][report["split"]]
JUDGED_SCORERS = list(split["metrics"])

# 사례별 회귀는 늘 통과하던 사례 중 이번에 평가한 것만 봅니다.
# Full경우의 전체 Stable사례랑, Smoke(대표사례)의 경우의 통과 사례를 얻음
stable_in_scope = []
for case_id in baseline["stable_cases"]:
    if case_id in report["cases"]:
        stable_in_scope.append(case_id)


def test_same_cases():
    # 평가 완전성: 기준선과 같은 사례로 평가해야 지표를 비교할 수 있습니다(순서는 무시하려고 정렬).
    # split["case_ids"] : full 혹은 smoke 중 하나에 대한 baseline결과
    assert sorted(report["cases"].keys()) == sorted(split["case_ids"]), "기준선과 다른 사례로 평가했습니다"


def test_no_scoring_errors():
    # 평가 완전성: 채점 오류가 난 칸은 판정이 비어 있어 지표를 믿을 수 없습니다.
    assert report["errors"] == 0, f"채점 오류 {report['errors']}건"


# parametrize: 채점 함수마다 테스트를 따로 실행합니다.
@pytest.mark.parametrize("name", JUDGED_SCORERS)
def test_metric_floor(name):
    # 절대 하한: 이번 지표가 팀이 정한 최소 품질 이상이어야 합니다.
    current = report["metrics"][name]
    assert current >= split["absolute_floor"][name], f"{name} {current} 가 절대 하한 {split['absolute_floor'][name]} 보다 낮습니다"


@pytest.mark.parametrize("name", JUDGED_SCORERS)
def test_metric_drop(name):
    # 허용 하락폭: 기준선 대비 하락폭이 허용값 이하여야 합니다(오르면 음수라 통과, 소수 오차는 반올림으로 제거).
    # 대표 baserun의 지표 - 현재 실험의 지표
    drop = round(split["metrics"][name] - report["metrics"][name], 4)
    assert drop <= split["allowed_drop"][name], f"{name} 가 기준선보다 {drop} 떨어졌습니다(허용 {split['allowed_drop'][name]})"


# parametrize: 사례마다 따로 실행해 실패한 case_id 가 바로 보입니다.
@pytest.mark.parametrize("case_id", stable_in_scope)
def test_stable_case_still_passes(case_id):
    # 사례별 회귀: 평균이 허용 범위 안이어도, 늘 통과하던 사례가 새로 실패하면 잡습니다.
    case = report["cases"][case_id]
    for name in JUDGED_SCORERS:
        assert case[name] is True, f"{case_id}: 기준선에서 늘 통과하던 질문이 {name} 에서 실패했습니다"


# 4가지
# (1) 평가 완전성 : 현재 Report가 baseline의 case와 같은지 및 평가시 에러가 없는지
# (2) 절대 하한 : 현재 report의 지표별 평균 점수가 절대 하한 아래인지 위인지
# (3) 상대적 하한 ; 현재 report의 지표별 평균 점수가 baseline대비 허용하락폭 위인지
# (4) 회귀 체크 : baseline에서 모두 통과한 안정적인 사례가, 현재 Report에서 성공했는지

# => 4가지를 모두 통과해야만 github코드에 main브랜치로 통합하겠다!