# Definition of Done

Writing this before any code. I'll only tick something if I can put a number, output or link next to it.

Screenshots referred to below (1.png, 2.png, ...) are attached to the pull request description.

## Must have (items 1-4)

- ✅ endpoint counts for task #1 match expected_counts.json from the COCO file, all 80 labels, total 7204
  - `GET /api/annotation-counts/1` -> `HTTP 200 total 7204 labels 80 top3 [('person', 2251), ('chair', 397), ('car', 347)]`
  - compared per label against the COCO file in the Django shell: `total 7204 mismatch none`
  - note: 79 of the 80 labels have objects in these 1000 images, the 80th correctly shows 0
- ✅ counting happens in one DB query, not in python
  - Django shell with DEBUG query log: `queries: 1` (shapes, tracks and tags in one UNION ALL, `cvat/apps/test/counting.py`)
- ✅ page in CVAT UI that calls the endpoint, reachable from the task page
  - route `/tasks/:tid/annotation-counts`, "Annotation counts" in the task Actions menu, screenshot 1.png
- ✅ counts shown as a bar chart
  - screenshot 1.png, person 2,251 on top, bars in the label colours
- ✅ task with no annotations shows an empty message instead of an empty chart
  - task #2 (3 images, no annotations), screenshot 3.png: "This task has no annotations yet"
- ✅ failed request shows an error with a retry button
  - `/tasks/999/annotation-counts`, screenshot 4.png: "Could not load annotation counts / No Task matches the given query." + Retry

## After that

- ✅ no login -> 401, logged in user without access to the task -> 403, admin -> 200
  ```
  == admin            HTTP 200 total 7204 labels 80
  == no login         {"detail":"Authentication credentials were not provided."}  HTTP 401
  == noaccess user    {"detail":"You do not have permission to perform this action."}  HTTP 403
  ```
  also covered by `test_no_login_is_rejected` and `test_user_without_access_to_task_is_rejected`
- ✅ MO-1 measured 5 times, raw output in OBJECTIVES.md, median + spread
  - median 63.9 ms, run medians 61.7 - 72.6 ms
- ✅ MO-1 met, or missed and I wrote down why
  - missed by 3.9 ms, the count query is ~13 ms of it, reasons and what I tried are in OBJECTIVES.md
- ✅ job filter works and the 10 job counts add up to the task total
  - per job via the API: `714 746 708 730 643 862 753 766 670 612`, sum = 7204. Screenshot 2.png (Job #1 = 714)
- ✅ chart updates without refresh when I save annotations in another tab
  - server side checked: socket got `{"event": "changed"}` 186 ms after the PATCH that added a shape, total went 7204 -> 7205, back to 7204 after deleting it
  - browser, on :8080: drew a person box in job 1 in another tab and saved, page went to 7,205 / person 2,252 without a reload, screenshot 5.png. Deleted it, back to 7,204.
- ✅ page reconnects after the server connection drops and shows current counts
  - `docker restart cvat_server` with the page open: tag went to "Reconnecting…", screenshot 6.png
  - came back to "Live" by itself once the server was up, counts 7,204, screenshot 7.png
- ✅ decision record at the bottom of PLAN.md

## General

- ✅ plan is the first commit, before code: `3ba33d264` at 02:52, first code commit `236ec7b5d` at 02:59
- ✅ no dead code / commented out code / random files in the diff
  - `git diff --stat d4d08dedb..HEAD`: everything is under cvat/apps/test, the new UI page folder and docs/, plus small hooks in asgi.py, urls.py, settings/base.py, cvat-app.tsx, the task actions menu and `ws: true` in the dev proxy. grep for print/console.log/TODO in the added lines: nothing.
- ✅ backend tests for counts and permissions pass
  ```
  PYTHONPATH=/tmp/localtest python3 manage.py test --settings container_testing cvat.apps.test -v 2
  (container_testing = cvat.settings.testing with IAM_OPA_URL = "http://opa:8181")
  Ran 9 tests in 0.277s
  OK
  ```
- ✅ everything I didn't finish is listed below with the reason
- ✅ PR from dev-test01 into develop on stackadnan/cvat (develop is CVAT's main branch)
  - https://github.com/stackadnan/cvat/pull/1

## Didn't finish

- **MO-1 target.** 63.9 ms against 60 ms. What I'd try next is caching the counts and clearing the cache from the same Job.touch() hook the websocket uses. Didn't do it because the laptop slept for ~3.5 h and the time went to finishing items 8-10.
- **Live updates from imports.** Saves from the annotation editor push updates (tested). Uploading annotations runs in `cvat_worker_import`. In my local setup only `cvat_server` has my code mounted, the workers still run the image built before the app existed, so an import doesn't push an update here. After a full rebuild from this branch the workers would have it too, but I haven't tested that.
- **Frontend tests.** No unit tests for the page or the reconnect hook, only the manual checks above with screenshots.
