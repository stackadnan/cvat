# Plan

Started: 22 Nov 2026, 02:40 PKT. 8 hours, so I need to be done by 10:40.

CVAT commit I cloned: d4d08dedb5ad7c5e980c0bc7319a7f5587365dad (branch dev-test01)

Data: I made task #1 with the first 1000 images of COCO val2017 (sorted by file name), 100 frames per job so 10 jobs, 80 labels. Imported instances_val2017.json filtered down to those 1000 images.

## Things I checked before planning

- Shapes are stored in LabeledShape (cvat/apps/engine/models.py). The class is the `label` foreign key -> Label.name. To get from a task to its shapes: Task -> Segment -> Job -> LabeledShape. Tracks and tags work the same way through Job.
- After importing COCO, CVAT has 8109 shapes but the COCO file only has 7204 objects. Objects with more than one polygon part get split into several shapes with the same `group` number. So if I just count rows my numbers won't match the source file.
- Annotations get saved with bulk_create (dataset_manager/task.py), so post_save signals don't fire. Need to remember this for the live update part.
- The server already runs on uvicorn/ASGI with 2 processes, so websockets should be possible without adding a new server, but a message has to reach both processes (redis is already there).
- Basic auth is really slow here, about 525ms per request just for password hashing, so I'll use token auth for timing.

## Decisions

- Count objects, not raw shapes. Ungrouped shape = 1, grouped shapes = 1 per (job, frame, group, label), track = 1, tag = 1. Skeleton child points not counted separately. This gives exactly 7204 for task #1 so I have a known answer to test against.
- Do the counting in the DB with a GROUP BY instead of loading annotations through dataset_manager (that loads every point, way too heavy just to count).
- Use CVAT's existing TaskPermission for access checks instead of writing my own.
- New django app `test` (cvat/apps/test). Endpoint: GET /api/annotation-counts?task_id=<id>, optional &job_id=<id>
- Extra filter: by job. Jobs are how work is split between annotators so per job counts seem the most useful thing to add.

## Order + rough time

1. docs (this) - 30 min
2. app + query + endpoint + permission check + tests - 1h15
3. UI page + route + link from task page - 45 min
4. bar chart - 30 min
5. empty state + error state with retry - 20 min
6. show 401/403 with a second user - 15 min
7. measure MO-1, 5 runs - 30 min
8. job filter - 30 min
9. websocket live updates + reconnect, only if 1-8 work - 1h45
10. tick DoD, open PR - 20 min
11. loom - 20 min

Not starting anything after step 5 until the page actually works in the browser.

## Skipping

- project level counts, task is enough
- caching (only if I miss the speed target)
- video / interpolated per-frame counts, a track counts as 1
- frontend unit tests, I'll check by hand and take screenshots

## Changes

- 03:00 - endpoint is `GET /api/annotation-counts/<task_id>` instead of `?task_id=`. With the id in the path DRF loads the task itself and CVAT's PolicyEnforcer calls my permission class with that task as the object, so I don't have to parse and look up task_id by hand before the access check.
- 03:20 - running the Django tests needed the testing requirements installed in the server container and OPA pointed at `opa:8181` (development settings hardcode localhost). Took ~15 min I hadn't planned for, but backend was still ahead of the budget.
