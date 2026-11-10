"""Administrator-only scope and resource limits. No network on validation."""
from dataclasses import dataclass
import ipaddress
import json

from app.dedicated import _secret

PRIVATE = tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))


def internal(address):
    return any(address in n for n in PRIVATE) and not (address.is_loopback or address.is_multicast or address.is_link_local)


@dataclass(frozen=True)
class Policy:
    networks: tuple
    ports: tuple = (22,80,443)
    max_targets: int = 64
    concurrency: int = 8
    target_timeout: float = 1.0
    job_timeout: float = 60.0
    max_jobs: int = 2

    @classmethod
    def load(cls, path):
        value=json.loads(_secret(path))
        return cls.from_mapping(value)

    @classmethod
    def from_mapping(cls, value):
        allowed={'networks','ports','max_targets','concurrency','target_timeout','job_timeout','max_jobs'}
        if not isinstance(value,dict) or set(value)!=allowed:raise ValueError('Configuração Discovery inválida.')
        if not isinstance(value['networks'],list) or not 1<=len(value['networks'])<=32:raise ValueError('Indique redes internas explícitas.')
        networks=tuple(ipaddress.IPv4Network(n,strict=True) for n in value['networks'])
        if not all(any(n.subnet_of(private) for private in PRIVATE) for n in networks):raise ValueError('Só são permitidas redes RFC1918.')
        ports=value['ports']
        if not isinstance(ports,list) or not 1<=len(ports)<=4 or len(set(ports))!=len(ports) or any(type(p) is not int or not 1<=p<=65535 for p in ports):raise ValueError('Portas inválidas.')
        for name,maximum in [('max_targets',256),('concurrency',32),('max_jobs',4)]:
            if type(value[name]) is not int or not 1<=value[name]<=maximum:raise ValueError('Limite inválido.')
        for name,maximum in [('target_timeout',5),('job_timeout',300)]:
            if type(value[name]) not in (float,int) or not .1<=value[name]<=maximum:raise ValueError('Timeout inválido.')
        return cls(networks,tuple(ports),**{k:v for k,v in value.items() if k not in {'networks','ports'}})

    def snapshot(self):
        return dict(networks=[str(n) for n in self.networks],ports=list(self.ports),max_targets=self.max_targets,
            concurrency=self.concurrency,target_timeout=self.target_timeout,job_timeout=self.job_timeout,max_jobs=self.max_jobs)

    def targets(self, value):
        if not isinstance(value,str) or len(value)>80:raise ValueError('Indique um CIDR IPv4 ou intervalo início-fim.')
        value=value.strip()
        try:
            if '/' in value:
                network=ipaddress.IPv4Network(value,strict=True)
                total=network.num_addresses if network.prefixlen>=31 else network.num_addresses-2
                if total>self.max_targets:raise ValueError('Demasiados alvos.')
                addresses=tuple(network.hosts())
            else:
                parts=value.split('-')
                if len(parts)!=2:raise ValueError('Use CIDR ou início-fim.')
                first,last=(ipaddress.IPv4Address(part.strip()) for part in parts)
                count=int(last)-int(first)+1
                if not 1<=count<=self.max_targets:raise ValueError('Intervalo inválido ou demasiado grande.')
                addresses=tuple(ipaddress.IPv4Address(n) for n in range(int(first),int(last)+1))
            if not addresses or not all(internal(a) and any(a in n for n in self.networks) for a in addresses):raise ValueError('Alvos fora das redes autorizadas.')
        except (ipaddress.AddressValueError,ipaddress.NetmaskValueError):
            raise ValueError('Rede IPv4 inválida.') from None
        return tuple(str(a) for a in addresses)
