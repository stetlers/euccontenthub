---
inclusion: auto
---

# Interactive Tour Maintenance

The EUC Content Hub has an interactive feature tour (`InteractiveTour` class) that walks users through the platform's key features. It lives in both `frontend/app.js` and `frontend/app-staging.js`.

## When to update the tour

Whenever a new user-facing feature is added to the site, the tour should be updated to include it. This means:

1. Add a new entry to the `FEATURES` array in the `InteractiveTour` class (both `app.js` and `app-staging.js`) with id, num, icon, name, tag, color, shortDesc, description, and bullets.
2. Add a corresponding hotspot position in `HOTSPOT_POSITIONS` with x/y coordinates (as percentages) that align with where the feature appears on the site diagram.
3. Update the site diagram in `renderDiagram()` if the new feature has a visible region on the page (add a new `data-region` div).
4. Update the step count references (e.g., "X of 12" becomes "X of 13") — these are derived from `FEATURES.length` so they update automatically.
5. Reset `tour_completed` consideration: when significant new features are added, consider whether existing users should be re-prompted. The "What's New" prompt already triggers for 30+ day absences, but a manual reset of `tour_completed` to `false` for all users could be done via a DynamoDB script if the feature is significant enough.

## Tour architecture quick reference

- **Class**: `InteractiveTour` in `frontend/app.js` and `frontend/app-staging.js`
- **Auth integration**: `frontend/auth.js` and `frontend/auth-staging.js` (auto-launch, "What's New" prompt, dropdown menu item)
- **Backend**: `lambda_api/lambda_function.py` — `tour_completed` field on user profiles, with a dedicated fast-path in `update_user_profile` for tour-only updates
- **Persistence**: `tour_completed` boolean in `euc-user-profiles` DynamoDB table
- **Trigger logic**: auto-launch if `tour_completed` is falsy, "What's New" banner if `tour_completed` is true but `last_visit_date` is 30+ days ago

## Spec reminder

When creating a spec for a new feature, include a task to update the interactive tour as part of the implementation plan. This ensures new features are discoverable by both new and returning users.
