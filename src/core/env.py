"""
프로젝트 루트 `.env`를 한 번 로드한다.

모든 에이전트·노드가 `OPENAI_API_KEY` 등을 읽기 **전에** 이 모듈을 import 하면
작업 디렉터리와 무관하게 동일한 키를 사용한다.
"""

from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _PROJECT_ROOT / ".env"

# override=False: 셸에 이미 export 된 값은 유지
load_dotenv(_ENV_PATH, override=False)
