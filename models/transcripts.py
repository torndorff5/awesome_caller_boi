from dataclasses import dataclass

@dataclass
class Transcript:
    phone_number: str
    call_text: str

    def __repr__(self):
        return f"Transcript(phone_number={self.phone_number!r}, call_text={self.call_text!r})"