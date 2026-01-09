# Google OAuth Setup Guide for Two-Way Calendar Sync

This guide walks you through setting up Google OAuth credentials to enable two-way calendar synchronization between LeadGen Pro and Google Calendar.

## What You'll Achieve
- **Push Events**: Meetings created in LeadGen Pro automatically appear in Google Calendar
- **Pull Events**: Import existing Google Calendar events into LeadGen Pro
- **Sync Updates**: Changes in either system reflect in the other
- **Attendee Management**: Sync meeting attendees and their responses

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top of the page
3. Click **"New Project"** in the popup
4. Enter project details:
   - **Project Name**: `LeadGen Pro Calendar Sync` (or your preference)
   - **Organization**: Leave as default or select your organization
5. Click **"Create"**
6. Wait for the project to be created (30 seconds - 1 minute)

---

## Step 2: Enable Google Calendar API

1. With your new project selected, go to [API Library](https://console.cloud.google.com/apis/library)
2. Search for **"Google Calendar API"**
3. Click on **"Google Calendar API"**
4. Click **"Enable"**
5. Wait for the API to be enabled

---

## Step 3: Configure OAuth Consent Screen

Before creating credentials, you must configure the consent screen (what users see when authorizing):

1. Go to [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
2. Select **"External"** user type (unless you have Google Workspace, then select Internal)
3. Click **"Create"**

### Fill in App Information:
- **App name**: `LeadGen Pro`
- **User support email**: Your email address
- **App logo**: (Optional) Upload your company logo
- **App domain** (optional): Your company website
- **Developer contact email**: Your email address

4. Click **"Save and Continue"**

### Add Scopes:
1. Click **"Add or Remove Scopes"**
2. Find and select these scopes:
   - `https://www.googleapis.com/auth/calendar` - Full calendar access
   - `https://www.googleapis.com/auth/calendar.events` - Manage events
   - `https://www.googleapis.com/auth/calendar.readonly` - View calendars
3. Click **"Update"**
4. Click **"Save and Continue"**

### Add Test Users (if External):
1. Click **"Add Users"**
2. Add your email and any team members who will use the sync
3. Click **"Save and Continue"**

4. Review the summary and click **"Back to Dashboard"**

---

## Step 4: Create OAuth 2.0 Credentials

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **"+ Create Credentials"**
3. Select **"OAuth client ID"**
4. Choose **"Web application"** as the application type
5. Configure:
   - **Name**: `LeadGen Pro Web Client`
   
   - **Authorized JavaScript origins**:
     ```
     https://leadgen-pro-24.preview.emergentagent.com
     ```
   
   - **Authorized redirect URIs**:
     ```
     https://leadgen-pro-24.preview.emergentagent.com/api/google/calendar/callback
     ```

6. Click **"Create"**

---

## Step 5: Save Your Credentials

After creating the credentials, you'll see a popup with:
- **Client ID**: `xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xxxxxxxxxxxxxxxxxxxxxx`

**IMPORTANT**: Save these credentials securely! You'll need to provide them to complete the integration.

### Download JSON (Recommended)
1. Click **"Download JSON"** to save a backup
2. Store this file securely

---

## Step 6: Provide Credentials to LeadGen Pro

Share the following with me:
1. **Client ID**
2. **Client Secret**

I will then:
1. Add them to the backend `.env` file
2. Implement the OAuth flow
3. Create the two-way sync endpoints
4. Add a "Connect Google Calendar" button to your settings

---

## Security Notes

- Your credentials are stored securely in environment variables
- Tokens are encrypted before database storage
- Users must explicitly authorize the calendar access
- You can revoke access at any time from Google Account settings

---

## Publishing Your App (Optional)

While in development, only test users can use the sync. To allow all users:

1. Go to [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
2. Click **"Publish App"**
3. Complete the verification process (may require Google review for sensitive scopes)

---

## Troubleshooting

### "Access blocked" error
- Make sure the user is added as a test user
- Or publish the app for production use

### "Invalid redirect URI" error
- Verify the redirect URI exactly matches what's in Cloud Console
- Check for trailing slashes

### "Insufficient permissions" error
- Ensure the Calendar API is enabled
- Check that the required scopes are added

---

## Next Steps

Once you provide the OAuth credentials:
1. I'll implement the calendar sync endpoints
2. Add a "Connect Calendar" button in Settings
3. Create sync status indicators
4. Set up automatic sync intervals

**Ready to proceed? Share your Client ID and Client Secret!**
