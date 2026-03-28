"""
Convert numeric amounts to Indian English words.
Uses num2words with Indian locale adjustments.
"""
try:
    from num2words import num2words as _num2words
    _HAS_NUM2WORDS = True
except ImportError:
    _HAS_NUM2WORDS = False


_LOWERCASE_CONJUNCTIONS = {'and', 'or', 'of', 'the'}


def _title_case_preserve_conjunctions(text):
    """Title-case a string but keep conjunctions like 'and' lowercase."""
    words = text.split()
    result = []
    for i, word in enumerate(words):
        lower = word.lower()
        if i == 0 or lower not in _LOWERCASE_CONJUNCTIONS:
            result.append(word.capitalize())
        else:
            result.append(lower)
    return ' '.join(result)


def _indian_num2words(n):
    """Convert integer part to Indian numbering words."""
    if n == 0:
        return 'Zero'

    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
            'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def two_digit(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')

    def three_digit(n):
        if n >= 100:
            return ones[n // 100] + ' Hundred' + (' and ' + two_digit(n % 100) if n % 100 else '')
        return two_digit(n)

    result = ''
    if n >= 10000000:  # Crore
        result += three_digit(n // 10000000) + ' Crore '
        n %= 10000000
    if n >= 100000:  # Lakh
        result += two_digit(n // 100000) + ' Lakh '
        n %= 100000
    if n >= 1000:  # Thousand
        result += two_digit(n // 1000) + ' Thousand '
        n %= 1000
    if n > 0:
        result += three_digit(n)
    return result.strip()


def amount_to_words(amount, currency='INR'):
    """Convert float amount to words. E.g. 62790.00 → 'INR Sixty Two Thousand Seven Hundred and Ninety only'"""
    if amount is None:
        amount = 0.0
    amount = float(amount)
    rupees = int(amount)
    paise = round((amount - rupees) * 100)

    if _HAS_NUM2WORDS:
        try:
            # title() gives wrong capitalisation for conjunctions like 'and'
            words = _num2words(rupees, lang='en_IN')
            words = _title_case_preserve_conjunctions(words)
        except Exception:
            words = _indian_num2words(rupees)
    else:
        words = _indian_num2words(rupees)

    result = f"{currency} {words}"
    if paise:
        if _HAS_NUM2WORDS:
            try:
                paise_words = _num2words(paise, lang='en_IN')
                paise_words = _title_case_preserve_conjunctions(paise_words)
            except Exception:
                paise_words = _indian_num2words(paise)
        else:
            paise_words = _indian_num2words(paise)
        result += f" and {paise_words} Paise"
    result += " only"
    return result
