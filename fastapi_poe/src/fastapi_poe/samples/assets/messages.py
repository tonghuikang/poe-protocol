UPDATE_IMAGE_PARSING = """\
I am parsing your resume with Tesseract OCR ...

---

"""

# TODO: show an image, if Markdown support for that happens before image upload
UPDATE_LLM_QUERY = """\
I have received your resume.

{resume}

I am querying the language model for analysis ...

---

"""

MULTIWORD_FAILURE_REPLY = """\
Please only send a URL.
Do not include any other words in your reply.

These are examples of resume the bot can accept.

https://raw.githubusercontent.com/jakegut/resume/master/resume.png

https://pjreddie.com/static/Redmon%20Resume.pdf

https://i.imgur.com/XYyvW6B.png

https://media.discordapp.net/attachments/1070915874996895744/1070915875139506296/jake.jpg

See https://poe.com/huikang/1512927999933968 for an example of an interaction.

You can also try https://poe.com/xyzFormatter for advice specifically on your bullet points.
"""

PARSE_FAILURE_REPLY = """
I could not load your resume.
Please check whether the link is publicly accessible.

---

If you are uploading to Github, please ensure that you are sending something like

https://raw.githubusercontent.com/jakegut/resume/master/resume.png

rather than

https://github.com/jakegut/resume/blob/master/resume.png

To get to raw.githubusercontent.com from github.com, right click "Download" and "Copy link address".

---

If you are uploading to imgur, please ensure that you are sending something like

https://i.imgur.com/XYyvW6B.png

rather than

https://imgur.com/a/6AeB8Vy

To get i.imgur.com from imgur.com, right click the image and "Copy image address".

---

This bot is not able to accept links from Google drive.

Remember to redact sensitive information, especially contact details.
"""
