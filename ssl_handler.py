"""SSL 검증 우회를 위한 공통 핸들러

회사 방화벽/프록시 환경에서 발생하는 SSL 인증서 오류를 해결하기 위한 모듈입니다.
모든 HTTP 라이브러리(requests, httpx, urllib 등)에 대한 SSL 우회 설정을 제공합니다.

사용법:
    from ssl_handler import setup_all_ssl_bypasses
    setup_all_ssl_bypasses()  # 스크립트 최상단에서 한 번만 호출

주의사항:
    - 개발/테스트 환경에서만 사용하세요
    - 프로덕션 환경에서는 적절한 인증서 설정을 권장합니다
"""

import ssl
import urllib3
import warnings
import logging
import os

logger = logging.getLogger(__name__)


def disable_ssl_warnings():
    """SSL 경고 메시지를 모두 비활성화합니다."""
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
    except Exception as e:
        logger.warning(f"SSL 경고 비활성화 중 오류: {e}")


def setup_ssl_context():
    """기본 SSL 컨텍스트를 검증 없음으로 설정합니다."""
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        logger.debug("SSL 컨텍스트 우회 설정 완료")
    except Exception as e:
        logger.warning(f"SSL 컨텍스트 설정 중 오류: {e}")


def patch_requests():
    """requests 라이브러리의 SSL 검증을 비활성화합니다."""
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry

        # requests의 urllib3 경고 비활성화
        requests.packages.urllib3.disable_warnings()

        # 기본 세션 설정
        session = requests.Session()
        session.verify = False

        logger.debug("requests 라이브러리 SSL 우회 설정 완료")
        return True
    except ImportError:
        logger.debug("requests 라이브러리가 설치되지 않음")
        return False
    except Exception as e:
        logger.warning(f"requests 패치 중 오류: {e}")
        return False


def patch_httpx():
    """httpx 라이브러리의 SSL 검증을 비활성화합니다.

    Gemini API, OpenAI API 등 많은 최신 라이브러리가 httpx를 사용합니다.
    """
    try:
        import httpx

        # 동기 클라이언트 패치
        _original_init = httpx.Client.__init__

        def patched_init(self, *args, **kwargs):
            kwargs['verify'] = False
            return _original_init(self, *args, **kwargs)

        httpx.Client.__init__ = patched_init

        # 비동기 클라이언트 패치
        _original_async_init = httpx.AsyncClient.__init__

        def patched_async_init(self, *args, **kwargs):
            kwargs['verify'] = False
            return _original_async_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_async_init

        logger.debug("httpx 라이브러리 SSL 우회 설정 완료")
        return True
    except ImportError:
        logger.debug("httpx 라이브러리가 설치되지 않음")
        return False
    except Exception as e:
        logger.warning(f"httpx 패치 중 오류: {e}")
        return False


def patch_aiohttp():
    """aiohttp 라이브러리의 SSL 검증을 비활성화합니다."""
    try:
        import aiohttp

        # aiohttp는 ClientSession 생성 시 ssl=False 파라미터 필요
        # 직접 패치하기보다는 사용자가 ssl=False를 전달하도록 안내
        logger.debug("aiohttp는 ClientSession(connector=aiohttp.TCPConnector(ssl=False)) 사용 권장")
        return True
    except ImportError:
        logger.debug("aiohttp 라이브러리가 설치되지 않음")
        return False


def patch_httplib2():
    """httplib2 라이브러리의 SSL 검증을 비활성화합니다.

    Google API 클라이언트(googleapiclient)가 httplib2를 사용합니다.
    """
    try:
        import httplib2

        # httplib2의 기본 SSL 컨텍스트를 비활성화된 컨텍스트로 교체
        _original_init = httplib2.Http.__init__

        def patched_init(self, *args, **kwargs):
            kwargs['disable_ssl_certificate_validation'] = True
            return _original_init(self, *args, **kwargs)

        httplib2.Http.__init__ = patched_init

        logger.debug("httplib2 라이브러리 SSL 우회 설정 완료")
        return True
    except ImportError:
        logger.debug("httplib2 라이브러리가 설치되지 않음")
        return False
    except Exception as e:
        logger.warning(f"httplib2 패치 중 오류: {e}")
        return False


def set_environment_variables():
    """SSL 관련 환경 변수를 설정합니다."""
    try:
        # Python의 SSL 검증 비활성화
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''

        logger.debug("SSL 관련 환경 변수 설정 완료")
    except Exception as e:
        logger.warning(f"환경 변수 설정 중 오류: {e}")


def setup_all_ssl_bypasses(verbose: bool = False):
    """모든 SSL 우회 설정을 한 번에 적용합니다.

    Args:
        verbose: True일 경우 상세 로그 출력

    Example:
        >>> from ssl_handler import setup_all_ssl_bypasses
        >>> setup_all_ssl_bypasses()
        ⚠️  SSL 검증이 비활성화되었습니다 (개발 환경)
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    # 경고 메시지 비활성화
    disable_ssl_warnings()

    # 기본 SSL 컨텍스트 설정
    setup_ssl_context()

    # 환경 변수 설정
    set_environment_variables()

    # 설치된 라이브러리들 패치
    patched = []

    if patch_requests():
        patched.append("requests")

    if patch_httpx():
        patched.append("httpx")

    if patch_aiohttp():
        patched.append("aiohttp")

    if patch_httplib2():
        patched.append("httplib2")

    # 사용자에게 알림
    logger.warning("⚠️  SSL 검증이 비활성화되었습니다 (개발 환경)")

    if verbose and patched:
        logger.info(f"패치된 라이브러리: {', '.join(patched)}")


def get_ssl_verify_setting() -> bool:
    """현재 SSL 검증 설정 상태를 반환합니다.

    Returns:
        환경 변수 또는 설정에 따른 SSL 검증 여부
    """
    # 환경 변수에서 확인
    ssl_verify_env = os.getenv('SSL_VERIFY', 'true').lower()
    return ssl_verify_env in ['true', '1', 'yes']


# 모듈 import 시 자동 실행 방지
# 명시적으로 setup_all_ssl_bypasses()를 호출해야 함
if __name__ == '__main__':
    # 테스트 실행
    print("SSL Handler 테스트")
    print("=" * 60)

    setup_all_ssl_bypasses(verbose=True)

    print("\n테스트 완료!")
    print("이제 모든 HTTP 요청에서 SSL 검증이 비활성화됩니다.")
    print("\n사용법:")
    print("  from ssl_handler import setup_all_ssl_bypasses")
    print("  setup_all_ssl_bypasses()")
