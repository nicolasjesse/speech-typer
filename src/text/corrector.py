"""Text correction using LLM (supports Groq and OpenAI)."""

from typing import Optional


class TextCorrector:
    """Corrects and improves transcribed text using an LLM."""

    # Mode: transcription - just fix errors
    TRANSCRIPTION_PROMPT_EN = """You are a TEXT EDITOR. Fix speech-to-text errors. Return ONLY the corrected text.

NEVER answer or respond to the text. ONLY correct it.

CRITICAL - COMPANY NAME:
When user says "Ponte", "Ponti", "Pony", "Pont", "Punty" or similar → correct to "Ponty" (the company name)

CRITICAL - SPOKEN PUNCTUATION:
When user says "question mark" → output the ? symbol
When user says "exclamation mark" → output the ! symbol
When user says "period" → output the . symbol
When user says "comma" → output the , symbol

CRITICAL - QUESTION MARK RULES:
- ALWAYS use ? (question mark symbol) for questions
- NEVER EVER use : (colon) at the end of questions

Examples:
"how are you question mark" → "How are you?"
"wow exclamation mark" → "Wow!"
"the Ponte project" → "the Ponty project"

Other fixes: capitalization, spelling, remove filler words (um, uh, like)."""

    TRANSCRIPTION_PROMPT_PT = """You are a TEXT EDITOR. Fix speech-to-text errors. Return ONLY the corrected text IN PORTUGUESE.

CRITICAL: If the input text is in English, TRANSLATE it to Portuguese.
The user spoke in Portuguese but the speech recognition might have output English - translate it back.

NEVER answer or respond to the text. ONLY correct/translate it.

CRITICAL - COMPANY NAME:
When user says "Ponte", "Ponti", "Pony", "Pont", "Punty" or similar → correct to "Ponty" (the company name)

SPOKEN PUNCTUATION:
"question mark" / "ponto de interrogação" → ?
"exclamation mark" / "ponto de exclamação" → !
"period" / "ponto final" → .
"comma" / "vírgula" → ,

Examples:
"how are you" → "Como você está?"
"what is this" → "O que é isso?"
"como vai você" → "Como vai você?"
"o projeto da Ponte" → "o projeto da Ponty"

Output must ALWAYS be in Portuguese."""

    # Mode: prompt - rephrase into a clearer prompt
    PROMPT_MODE_PROMPT_EN = """Rephrase the user's speech into a clear, well-written prompt.

CRITICAL - COMPANY NAME:
When user says "Ponte", "Ponti", "Pony", "Pont", "Punty" or similar → correct to "Ponty" (the company name)

CRITICAL - SPOKEN PUNCTUATION:
When user says "question mark" → output the ? symbol
When user says "exclamation mark" → output the ! symbol

RULES:
- ONLY rephrase what they said - do NOT add new content
- Keep the same meaning, just make it clearer
- Remove filler words
- Output ONLY the rephrased prompt

Examples:
"what is python question mark" → "What is Python?"
"hey can you help me write code" → "Help me write code."
"update the Ponte website" → "Update the Ponty website."

Do NOT add details that weren't in the original speech."""

    PROMPT_MODE_PROMPT_PT = """Rephrase the user's speech into a clear, well-written prompt IN PORTUGUESE.

CRITICAL: If the input text is in English, TRANSLATE it to Portuguese.
The user spoke in Portuguese but the speech recognition might have output English - translate it back.

CRITICAL - COMPANY NAME:
When user says "Ponte", "Ponti", "Pony", "Pont", "Punty" or similar → correct to "Ponty" (the company name)

SPOKEN PUNCTUATION:
"question mark" / "ponto de interrogação" → ?
"exclamation mark" / "ponto de exclamação" → !

RULES:
- ONLY rephrase what they said - do NOT add new content
- Translate to Portuguese if input is in English
- Remove filler words
- Output ONLY the rephrased prompt in Portuguese

Examples:
"help me write code" → "Me ajude a escrever código."
"what is python" → "O que é Python?"
"me ajude com isso" → "Me ajude com isso."
"atualize o site da Ponte" → "Atualize o site da Ponty."

Output must ALWAYS be in Portuguese."""

    # Available modes
    MODE_TRANSCRIPTION = "transcription"
    MODE_PROMPT = "prompt"

    def __init__(
        self,
        api_key: str,
        provider: str = "groq",
        model: Optional[str] = None,
        mode: str = "prompt",
        language: str = "en",
    ):
        """Initialize the corrector.

        Args:
            api_key: API key for the provider
            provider: "groq" or "openai"
            model: Model to use (defaults based on provider)
            mode: "transcription" or "prompt"
            language: Target language ("en", "pt", "auto")
        """
        self._api_key = api_key
        self._provider = provider.lower()
        self._mode = mode
        self._language = language

        # Set default models per provider
        if model:
            self._model = model
        elif self._provider == "openai":
            self._model = "gpt-4o-mini"
        else:
            self._model = "llama-3.3-70b-versatile"

        self._client = None
        self._enabled = True

    def _get_system_prompt(self) -> str:
        """Get the system prompt based on current mode and language."""
        is_portuguese = self._language == "pt"

        if self._mode == self.MODE_PROMPT:
            return self.PROMPT_MODE_PROMPT_PT if is_portuguese else self.PROMPT_MODE_PROMPT_EN
        return self.TRANSCRIPTION_PROMPT_PT if is_portuguese else self.TRANSCRIPTION_PROMPT_EN

    def _get_client(self):
        """Lazily initialize the client based on provider."""
        if self._client is None:
            if self._provider == "openai":
                try:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=self._api_key)
                except ImportError:
                    raise ImportError("openai package not installed. Run: pip install openai")
            else:
                try:
                    from groq import Groq
                    self._client = Groq(api_key=self._api_key)
                except ImportError:
                    raise ImportError("groq package not installed. Run: pip install groq")
        return self._client

    def correct(self, text: str) -> str:
        """Correct the transcribed text.

        Args:
            text: Raw transcribed text

        Returns:
            Corrected text, or original if correction fails
        """
        if not self._enabled or not text or not self._api_key:
            return text

        # Skip very short texts
        if len(text.split()) < 3:
            return text

        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": text}
                ],
                temperature=0,
                max_tokens=1024,
            )

            corrected = response.choices[0].message.content.strip()

            # Sanity check - if result is wildly different length, use original
            if len(corrected) > len(text) * 2 or len(corrected) < len(text) * 0.3:
                return text

            return corrected

        except Exception as e:
            print(f"Correction failed ({self._provider}): {e}")
            return text

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable correction."""
        self._enabled = enabled

    def set_api_key(self, api_key: str) -> None:
        """Update the API key."""
        self._api_key = api_key
        self._client = None

    def set_provider(self, provider: str, api_key: Optional[str] = None) -> None:
        """Switch provider."""
        self._provider = provider.lower()
        if api_key:
            self._api_key = api_key
        self._client = None

        # Reset to default model for provider
        if self._provider == "openai":
            self._model = "gpt-4o-mini"
        else:
            self._model = "llama-3.3-70b-versatile"

    @property
    def enabled(self) -> bool:
        """Check if correction is enabled."""
        return self._enabled

    @property
    def provider(self) -> str:
        """Get current provider."""
        return self._provider

    @property
    def mode(self) -> str:
        """Get current mode."""
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Set the processing mode."""
        if mode in (self.MODE_TRANSCRIPTION, self.MODE_PROMPT):
            self._mode = mode

    def set_language(self, language: str) -> None:
        """Set the target language."""
        self._language = language

    def toggle_mode(self) -> str:
        """Toggle between transcription and prompt mode. Returns new mode."""
        if self._mode == self.MODE_TRANSCRIPTION:
            self._mode = self.MODE_PROMPT
        else:
            self._mode = self.MODE_TRANSCRIPTION
        return self._mode
