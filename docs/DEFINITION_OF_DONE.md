# Definition of Done

Writing this before any code. I'll only tick something if I can put a number, output or link next to it.

## Must have (items 1-4)

- [ ] endpoint counts for task #1 match expected_counts.json from the COCO file, all 80 labels, total 7204
- [ ] counting happens in one DB query, not in python
- [ ] page in CVAT UI that calls the endpoint, reachable from the task page
- [ ] counts shown as a bar chart
- [ ] task with no annotations shows an empty message instead of an empty chart
- [ ] failed request shows an error with a retry button

## After that

- [ ] no login -> 401, logged in user without access to the task -> 403, admin -> 200
- [ ] MO-1 measured 5 times, raw output in OBJECTIVES.md, median + spread
- [ ] MO-1 met, or missed and I wrote down why
- [ ] job filter works and the 10 job counts add up to the task total
- [ ] chart updates without refresh when I save annotations in another tab
- [ ] page reconnects after the server connection drops and shows current counts
- [ ] decision record at the bottom of PLAN.md

## General

- [ ] plan is the first commit, before code
- [ ] no dead code / commented out code / random files in the diff
- [ ] backend tests for counts and permissions pass
- [ ] everything I didn't finish is listed below with the reason
- [ ] PR from dev-test01 into develop on stackadnan/cvat (develop is CVAT's main branch)

## Didn't finish

(fill in at the end)
