from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class OtpTestConf:
    owner: str = "test@example.com"
    code: str = "123456"
    ttl: int = 120

otp_test_conf = OtpTestConf()