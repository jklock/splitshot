from __future__ import annotations

from dataclasses import dataclass
from http.cookiejar import Cookie


_PRACTISCORE_DOMAIN = "practiscore.com"
_SUPPORTED_BROWSERS = (
    ("chrome", "chrome"),
    ("edge", "edge"),
    ("firefox", "firefox"),
    ("safari", "safari"),
    ("chromium", "chromium"),
    ("brave", "brave"),
    ("vivaldi", "vivaldi"),
    ("opera", "opera"),
    ("librewolf", "librewolf"),
)


@dataclass(frozen=True, slots=True)
class PractiScoreBrowserSession:
    browser_name: str
    cookies: list[dict[str, object]]


def load_practiscore_system_browser_session() -> PractiScoreBrowserSession | None:
    try:
        import browser_cookie3
    except Exception:
        return None

    best_session: PractiScoreBrowserSession | None = None
    for browser_name, attribute_name in _SUPPORTED_BROWSERS:
        loader = getattr(browser_cookie3, attribute_name, None)
        if not callable(loader):
            continue
        session = _load_browser_session(browser_name, loader)
        if session is None:
            continue
        if best_session is None or len(session.cookies) > len(best_session.cookies):
            best_session = session
    return best_session


def _load_browser_session(browser_name: str, loader) -> PractiScoreBrowserSession | None:
    try:
        cookie_jar = loader(domain_name=_PRACTISCORE_DOMAIN)
    except Exception:
        return None

    payloads: list[dict[str, object]] = []
    for cookie in cookie_jar:
        payload = _cookie_payload(cookie)
        if payload is not None:
            payloads.append(payload)
    if not payloads:
        return None
    return PractiScoreBrowserSession(browser_name=browser_name, cookies=payloads)


def _cookie_payload(cookie: Cookie) -> dict[str, object] | None:
    name = str(cookie.name or "").strip()
    value = str(cookie.value or "")
    domain = str(cookie.domain or "").strip()
    path = str(cookie.path or "/").strip() or "/"
    normalized_domain = domain.lower().lstrip(".")
    if not name or not value or not normalized_domain:
        return None
    if normalized_domain != _PRACTISCORE_DOMAIN and not normalized_domain.endswith(f".{_PRACTISCORE_DOMAIN}"):
        return None

    payload: dict[str, object] = {
        "name": name,
        "value": value,
        "domain": domain,
        "path": path,
        "secure": bool(cookie.secure),
    }
    if cookie.expires is not None:
        payload["expires"] = int(cookie.expires)

    rest = {str(key).lower(): value for key, value in dict(getattr(cookie, "_rest", {}) or {}).items()}
    if "httponly" in rest:
        payload["http_only"] = True
    same_site = str(rest.get("samesite") or "").strip()
    if same_site:
        payload["same_site"] = same_site
    return payload