def normalize_cpf(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def is_valid_cpf(value: str | None) -> bool:
    cpf = normalize_cpf(value)
    if len(cpf) != 11:
        return False
    if len(set(cpf)) == 1:
        return False

    for base in (9, 10):
        total = sum(int(cpf[i]) * ((base + 1) - i) for i in range(base))
        digit = (total * 10) % 11
        if digit == 10:
            digit = 0
        if digit != int(cpf[base]):
            return False

    return True
