---
phase: quick-1-after-user-login-email
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/SinodikApp.jsx
autonomous: true
requirements: [quick-1]
must_haves:
  truths:
    - "When logged in, order form email field shows user's login email"
    - "When logged in, email field is read-only so order is tied to that user"
    - "When guest, email field stays empty and editable"
  artifacts:
    - path: frontend/SinodikApp.jsx
      provides: AddPage with user prop; email prefill and readOnly when user
  key_links:
    - from: "Parent (App) user state"
      to: "AddPage"
      via: "user prop"
    - from: "AddPage form.userEmail"
      to: "user.email when user present"
      via: "useEffect sync + readOnly input"
---

<objective>
After login, the order form (записка) email field is pre-filled with the logged-in user's email and is read-only. Guest behaviour unchanged: empty, editable.
Purpose: Orders are clearly tied to the logged-in user; no editing of email when authenticated.
Output: AddPage receives optional `user` prop; when user is set, email is user.email and input is readOnly.
</objective>

<context>
@CLAUDE.md
- SinodikApp.jsx: AddPage (lines ~396–504) has form.userEmail; parent has user from /auth/me (line 1868); AddPage is rendered at lines 2153, 2158, 2165 without user prop. Email input at 686–692 (shown when form.notifyAccept).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Pass user into AddPage and wire email when logged in</name>
  <files>frontend/SinodikApp.jsx</files>
  <action>
1) Add optional prop to AddPage: `function AddPage({ user = null })`.
2) At all three call sites, pass user: `<AddPage user={user} />` (lines ~2153, 2158, 2165; for the first one user is always null so `user={null}` or just rely on default).
3) In AddPage: when `user` is present, keep form.userEmail in sync with user.email:
   - In a useEffect with dependency [user], if (user?.email) setForm(f => ({ ...f, userEmail: user.email })).
   - This pre-fills and keeps it in sync if user object reference changes.
4) When rendering the email input (the block that shows when form.notifyAccept): if `user` is present, set input to readOnly and do not call onChange for that input (or keep onChange but input is readOnly so it cannot be edited). Value remains form.userEmail (already synced to user.email).
5) On successful submit (setResult(data) and reset form): when resetting form, only clear userEmail if !user — i.e. set userEmail to (user?.email ?? "") so logged-in users keep their email in the form after submit.
  </action>
  <verify>
    <automated>Manual: open app, login, go to add tab, check "Уведомить о принятии" — email must show login email and be read-only. As guest, email must be empty and editable.</automated>
  </verify>
  <done>Logged-in user sees their email in the order form and cannot change it; guest sees empty editable field. Submit still sends correct user_email.</done>
</task>

</tasks>

<verification>
- Logged in: email field shows user.email, read-only.
- Guest: email field empty, editable.
- After submit when logged in, form keeps user email (no reset to empty).
</verification>

<success_criteria>
- AddPage accepts optional user prop; parent passes user at all three render sites.
- When user is set, form.userEmail is synced to user.email and the email input is readOnly.
- When user is not set, behaviour unchanged (empty, editable).
</success_criteria>

<output>
After completion, create `.planning/quick/1-after-user-login-field-e-mail-should-be-/1-SUMMARY.md` if the workflow expects it (quick mode may skip).
</output>
