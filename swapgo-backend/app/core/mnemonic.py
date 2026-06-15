from mnemonic import Mnemonic


def generate_mnemonic_words(strength_bits: int = 128, language: str = "english") -> str:
    return Mnemonic(language).generate(strength=strength_bits)
