import ipaddress
from functools import lru_cache

from fastapi import Request

from app.core.config import settings


@lru_cache(maxsize=8)
def _parse_trusted_networks(cidrs_tuple: tuple[str, ...]) -> list[ipaddress._BaseNetwork]:
    nets = []
    for cidr in cidrs_tuple:
        try:
            nets.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            continue
    return nets


def _is_trusted_proxy(ip_str: str) -> bool:
    if not ip_str:
        return False
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False
    nets = _parse_trusted_networks(tuple(settings.trusted_proxy_cidrs_list))
    return any(addr in net for net in nets)


def get_client_ip(request: Request | None) -> str:
    """
    Extract client IP safely.
    Only trusts X-Forwarded-For / X-Real-IP when the direct peer (request.client.host)
    is in TRUSTED_PROXY_CIDRS (e.g. nginx container).
    """
    if request is None or request.client is None:
        return "unknown"

    peer_ip = request.client.host or "unknown"
    if not _is_trusted_proxy(peer_ip):
        return peer_ip

    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        # Walk from right to left and return the first non-trusted IP (closest client)
        for candidate in reversed(parts):
            if not _is_trusted_proxy(candidate):
                return candidate
        if parts:
            return parts[0]

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()

    return peer_ip
