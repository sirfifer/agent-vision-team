Build a Python utility library called "texttools" with the following 10 functions. Each function goes in its own module file under texttools/. Write a corresponding test file for each function under tests/. Run all the tests at the end to verify everything works.

Your process:

- Create a task for each function (10 tasks total) using TaskCreate.
- Work through each task one at a time: implement the function module, write its test file, then mark the task complete before moving to the next.
- After all 10 functions are done, create one final task for running all the tests together.

The functions:

1. texttools/word_count.py - word_count(text: str) -> int: Count the number of words in the input text. Handle edge cases like multiple spaces and empty strings.

2. texttools/char_frequency.py - char_frequency(text: str) -> dict[str, int]: Return a dictionary mapping each character to its frequency count. Case-insensitive.

3. texttools/reverse_words.py - reverse_words(text: str) -> str: Reverse the order of words in the text while preserving spacing.

4. texttools/title_case.py - title_case(text: str) -> str: Convert text to title case, but keep articles (a, an, the, of, in) lowercase unless they start the string.

5. texttools/remove_duplicates.py - remove_duplicates(text: str) -> str: Remove duplicate words from the text, keeping the first occurrence of each.

6. texttools/extract_emails.py - extract_emails(text: str) -> list[str]: Extract all email addresses from the text using regex pattern matching.

7. texttools/wrap_text.py - wrap_text(text: str, width: int) -> str: Word-wrap text at the specified width. Never break mid-word.

8. texttools/strip_html.py - strip_html(text: str) -> str: Remove all HTML tags from the text, preserving the text content between tags.

9. texttools/generate_slug.py - generate_slug(text: str) -> str: Convert text to a URL-friendly slug (lowercase, hyphens instead of spaces, no special characters).

10. texttools/caesar_cipher.py - caesar_cipher(text: str, shift: int) -> str: Apply a Caesar cipher to alphabetic characters. Preserve case and non-alphabetic characters.

Also create texttools/__init__.py that imports all 10 functions for convenient access.

Each test file should have at least 3 test cases covering normal input, edge cases, and error conditions.
