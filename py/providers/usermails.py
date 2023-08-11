"""
models of email for user validation, email verification , password reset and admin and user status information
"""
__all__ = "MAIL_MODELS"
MAIL_MODELS: dict = dict(
    {
        "activate": {
            "en_EN": {
                "action": {
                    "create": "created",
                    "update": "updated",
                    "modify": "modified on request",
                },
                "url": "/gui/admin/users/activate/",
                "subject": "EcoTaxa account [{action}]",
                "link": '<a href="{url}{id}" style="color: rgb(52, 167, 173)">{url}{id}</a>',
                "email": '<a href="mailto:{email}">{email}</a>',
                "reason": '<ul><li><a href="{url}{id}?reason=email" style="color: rgb(52, 167, 173)">Invalid email</a></li><li><a href="{url}{id}?reason=organisation" style="color: rgb(52, 167, 173)">More info or incorrect organisation</a></li><li><a href="{url}{id}?reason=creation" style="color: rgb(52, 167, 173)">More info about the creation reason</a></li><li><a href="{url}{id}?reason=all" style="color: rgb(52, 167, 173)">email, organisation, creation reason</a></li></ul>',
                "body": "<p>Account [{action}]<br>{data}<br>Please click on the following link to validate the account  :<br>{link}<br>Or click the following link to ask the user to modify the information provided : {reason}</p><br>",
            }
        },
        "active": {
            "en_EN": {
                "active": {
                    "url": "/gui/login",
                    "subject": "EcoTaxa account activation.",
                    "link": '<a href="{url}" style="color: rgb(52, 167, 173)">{url}</a>',
                    "email": '<a href="mailto:{email}">{email}</a>',
                    "body": "<p>Your account has been activated.<br>You can now login to the EcoTaxa application and start creating a  project.{link}.<br>If you have any questions or need additional support,  email: {email}</p>",
                },
                "desactive": {
                    "subject": "EcoTaxa account desactivation.",
                    "email": '<a href="mailto:{email}">{email}</a>',
                    "body": "<p>Your account has been desactivated.<br>You cannot login to EcoTaxa anymore.<br>If you have any questions about your data or need additional support,  email: {email}</p>",
                },
                "modify": {
                    "url": "/gui/register/",
                    "subject": "EcoTaxa account modification request.",
                    "link": '<a href="{url}{token}" style="color: rgb(52, 167, 173)">{url}{token}</a>',
                    "email": '<a href="mailto:{email}">{email}</a>',
                    "reason": {
                        "email": "Please provide a professional or academic email. providers like gmail, hotmail and similar are not accepted to activate your account.",
                        "organisation": "Please provide a verified organisation name.",
                        "creation": "Please give some more details about the reason of your registration and EcoTaxa usage.",
                    },
                    "body": "<p>Some of the information provided in your profile need to be modified :<br>{reason}<br>Please click the following link to modify your registration information: {link}<br>If you have any questions about your data or need additional support,  email: {email}</p>",
                },
            }
        },
        "passwordreset": {
            "en_EN": {
                "url": "/gui/me/forgotten/",
                "subject": "EcoTaxa password reset.",
                "link": '<a href="{url}{token}" style="color: rgb(52, 167, 173)">{url}{token}</a>',
                "email": '<a href="mailto:{email}">{email}</a>',
                "body": '<p>Please click on the following link to rest your password : {link}<br>If you have any questions or need additional support,  email: {email}</p><p style="font-size:0.85rem">***If you are not the initiator of this request, ignore it.</p>',
            }
        },
        "verify": {
            "en_EN": {
                "create": {
                    "url": "/gui/register/",
                    "subject": "EcoTaxa account creation request - email verify ",
                    "link": '<a href="{url}{token}" style="color: rgb(52, 167, 173)">{url}{token}</a>',
                    "email": '<a href="mailto:{email}">{email}</a>',
                    "body": "<p>Welcome to the EcoTaxa registration process.<br>Please click on the following link to validate your email address and continue your account creation process: {link}.<br>If you have any questions or need additional support,  email: {email}</p>",
                },
                "update": {
                    "url": "/gui/me/activate/",
                    "subject": "EcoTaxa account modification request - email verify ",
                    "link": '<a href="{url}{token}" style="color: rgb(52, 167, 173)">{url}{token}</a>',
                    "email": '<a href="mailto:{email}">{email}</a>',
                    "body": "<p>Your account information have to be verified.  <br>Please click on the following link to validate your email address and continue your account modification process: {link}<br>If you have any questions or need additional support,  email: {email}</p>",
                },
            }
        },
    }
)
