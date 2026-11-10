"""TCP connect only: no commands, DNS, login, banners or application payload.

Persist fixed codes/errno, never exception strings or OS-supplied messages.
"""
import errno
import socket
import time

UNREACHABLE={getattr(errno,name):name for name in ('ENETUNREACH','EHOSTUNREACH','ENETDOWN','EHOSTDOWN') if hasattr(errno,name)}
LOCAL_ERRORS={getattr(errno,name):name for name in ('EACCES','EPERM','EADDRNOTAVAIL','EADDRINUSE','EMFILE','ENFILE','ENOBUFS','ENOMEM','EAFNOSUPPORT','EINVAL') if hasattr(errno,name)}


def classify_error(number):
    if number==errno.ECONNREFUSED:result,code='refused','ECONNREFUSED'
    elif number in {errno.ETIMEDOUT,errno.EAGAIN}:result,code='timeout',('ETIMEDOUT' if number==errno.ETIMEDOUT else 'EAGAIN')
    elif number in UNREACHABLE:result,code='unreachable',UNREACHABLE[number]
    elif number in LOCAL_ERRORS:result,code='local_error',LOCAL_ERRORS[number]
    else:result,code='error',('OS_ERROR_WITHOUT_ERRNO' if number is None else 'UNCLASSIFIED_CONNECT_ERROR')
    value=dict(result=result,code=code)
    if type(number) is int:value['errno']=number
    return value


def probe(ip, policy, cancelled=lambda: False, *, deadline=None):
    evidence=[]
    for port in policy.ports:
        if cancelled():break
        remaining=policy.target_timeout
        if deadline is not None:remaining=min(remaining,deadline-time.monotonic())
        if remaining<=0:break
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as connection:
                connection.settimeout(remaining)
                result=connection.connect_ex((ip,port))
            value=dict(result='connected') if result==0 else classify_error(result)
        except (TimeoutError,socket.timeout):value=dict(result='timeout',code='SOCKET_TIMEOUT')
        except OSError as error:value=classify_error(error.errno)
        evidence.append(dict(port=port,**value))
    results={e['result'] for e in evidence}
    # Any positive TCP evidence wins over failures of other ports. Refused alone
    # is a response, never a whole-target failure or proof of equipment identity.
    outcome='responded' if results & {'connected','refused'} else 'error' if results & {'error','local_error','unreachable'} else 'no_response'
    return dict(outcome=outcome,evidence=dict(method='tcp_connect',ports=evidence))
