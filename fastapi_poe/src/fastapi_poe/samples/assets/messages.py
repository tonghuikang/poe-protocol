UPDATE_IMAGE_PARSING = """\
I am parsing your resume with Tesseract OCR ...

---

"""

UPDATE_LLM_QUERY = """\
I am querying the language model for analysis ...

---

"""

MULTIPLE_WORDS_FAILURE_REPLY = """\
Please send a URL to an image or pdf of your resume.

Please only send a URL.
Do not include any other words in your reply.

This is an example

https://raw.githubusercontent.com/jakegut/resume/master/resume.png

This is another example

https://pjreddie.com/static/Redmon%20Resume.pdf
"""

PARSE_FAILURE_REPLY = """
I could not load your resume.
Please check whether the link is publicly accessible.

This is an example

https://raw.githubusercontent.com/jakegut/resume/master/resume.png

This is another example

https://pjreddie.com/static/Redmon%20Resume.pdf

You can upload your resume to sites like imgur or GitHub.
Remember to redact sensitive information.
"""
