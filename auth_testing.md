# Auth Testing Playbook for LeadGen Pro

## Overview
This playbook is used for testing the Google OAuth authentication flow implemented with Emergent Auth.

## Test Scenarios

### 1. Login Page UI Test
- [ ] Login page loads correctly
- [ ] "Sign in with Google" button is visible and has Google logo
- [ ] "or continue with email" separator is shown
- [ ] Email/Password form is visible
- [ ] "Don't have an account? Contact your administrator." message is shown

### 2. Google Sign-In Flow (Manual Test)
Since Google OAuth requires real Google authentication, this must be tested manually:
1. Click "Sign in with Google" button
2. Google authentication page should open
3. After Google auth, user is redirected back to /dashboard#session_id=xxx
4. AuthCallback component processes the session_id
5. Backend validates with Emergent Auth
6. If user email exists in database → Login success
7. If user email NOT in database → Show error "No account found"

### 3. Backend API Tests
```bash
# Test Google Auth endpoint with invalid session (should return 401)
curl -X POST "https://your-app.com/api/auth/google" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"invalid"}'

# Test traditional login (should still work)
curl -X POST "https://your-app.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}'
```

### 4. Admin-Only Account Creation Test
1. As admin, create an employee with email: `test.employee@gmail.com`
2. That employee should be able to sign in with Google using their Gmail
3. A user WITHOUT an account should see error: "No account found with this email"

## Test Credentials
- Admin: admin@test.com / admin123
- Admin emails for Google: mattmascasa@gmail.com, monika.iordanoff@gmail.com

## Success Criteria
✅ Login page shows Google Sign-In button
✅ Traditional email/password login still works
✅ Backend rejects invalid session_ids
✅ Backend allows login for existing users via Google
✅ Backend rejects login for non-existing users via Google
