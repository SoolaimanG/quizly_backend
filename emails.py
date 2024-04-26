def otp_message(otp: str):
    return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Your OTP Code</title>
  </head>

  <body style="font-family: 'Spectral', serif; background-color: #f4f4f4; padding: 20px;">

    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">

      <h2 style="text-align: center; color: #2ecc71;">Your OTP Code</h2>

      <p style="text-align: center; font-size: 16px; color: #555;">Use the following One-Time Password (OTP) to complete your action:</p>

      <div style="text-align: center; padding: 20px; background-color: #2ecc71; border-radius: 5px; font-size: 24px; color: #fff; font-weight: bold;">
        {otp}
      </div>

      <p style="text-align: center; font-size: 14px; color: #777;">This OTP is valid for a single use only. Please do not share it with anyone.</p>

      <p style="text-align: center; font-size: 14px; color: #777;">If you did not request this OTP, please ignore this email.</p>

    </div>
  </body>
</html>
"""


def survey_invitation(link: str):
  return f"""
  <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Survey Invitation</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f3f3f3;">
    <div style="max-width: 600px; margin: 20px auto; padding: 20px; background-color: #ffffff; border-radius: 10px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);">
        <h1 style="color: #4CAF50; text-align: center; margin-bottom: 20px;">Survey Invitation</h1>
        <p style="color: #333333; margin-bottom: 20px;">Hello there,</p>
        <p style="color: #333333; margin-bottom: 20px;">You've been invited to participate in a survey! Your opinion matters to us.</p>
        <p style="color: #333333; margin-bottom: 20px;">Click the button below to start the survey:</p>
        <p style="margin-bottom: 20px;"><a href={link} style="display: inline-block; padding: 8px 18px; background-color: #4CAF50; color: #ffffff; text-decoration: none; border-radius: 5px;">Take Survey</a></p>
        <p style="color: #333333; margin-bottom: 20px;">If the button above doesn't work, you can copy and paste the following link into your browser:</p>
        <p style="color: #333333; margin-bottom: 20px;">Survey Link: <a href={link} style="color: #4CAF50;">{link}</a></p>
        <p style="color: #333333;">Thank you for your participation!</p>
    </div>
</body>
</html>


"""


def verify_email_address(link: str):
    return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Email Confirmation</title>
  </head>

  <body style="font-family: 'Spectral', serif; background-color: #f4f4f4; padding: 20px;">

    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">

      <h2 style="text-align: center; color: #2ecc71;">Email Confirmation</h2>

      <p style="text-align: center; font-size: 16px; color: #555;">Thank you for registering. To complete your registration, please use the following button:</p>

      <div style="text-align: center; padding: 20px;">
        <a href={link} style="display: inline-block; background-color: #2ecc71; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 18px; font-weight: bold;">Confirm Email</a>
      </div>

      <p style="text-align: center; font-size: 14px; color: #777;">This confirmation link is valid for 25 minutes. Click the button to confirm your email.</p>

      <p style="text-align: center; font-size: 14px; color: #777;">If you did not register for this account, please ignore this email.</p>

    </div>

  </body>
</html>


"""