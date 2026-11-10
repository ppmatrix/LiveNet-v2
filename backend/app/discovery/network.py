"""TCP connect only: no commands, DNS, login, banners or application payload."""
import errno
import socket
import time


def probe(ip, policy, cancelled=lambda: False):
    evidence=[];deadline=time.monotonic()+policy.target_timeout
    for port in policy.ports:
        if cancelled():break
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as connection:
                connection.settimeout(remaining)
                result=connection.connect_ex((ip,port))
            outcome='connected' if result==0 else 'refused' if result==errno.ECONNREFUSED else 'timeout' if result in {errno.ETIMEDOUT,errno.EAGAIN} else 'error'
        except (TimeoutError,socket.timeout):outcome='timeout'
        except OSError:outcome='error'
        evidence.append(dict(port=port,result=outcome))
    outcome='responded' if any(e['result'] in {'connected','refused'} for e in evidence) else 'error' if any(e['result']=='error' for e in evidence) else 'no_response'
    return dict(outcome=outcome,evidence=dict(method='tcp_connect',ports=evidence))
