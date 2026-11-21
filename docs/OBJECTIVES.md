# Objectives

My machine:
- CPU: Intel i9-9980HK, 8 cores / 16 threads
- RAM: 32 GB (Docker Desktop set to 8 CPUs, 12 GB)
- OS: macOS 26.7.3, Docker 29.9.3
- CVAT commit: d4d08dedb5ad7c5e980c0bc7319a7f5587365dad
- Data: task #1, 1000 COCO val2017 images, 8109 shapes / 7204 objects, 80 labels

## MO-1

| ID | Field | Entry |
|---|---|---|
| MO-1 | What is measured | Total time for `GET /api/annotation-counts?task_id=1` (request sent to last byte back) |
| | How | curl with `-w '%{time_total}'` from my mac through traefik, token auth. 1 warm-up request then 20 in a row = 1 run. Take the median of the 20. Do 5 runs. |
| | Target | Median of the 5 runs <= 60 ms |
| | Conditions | local docker stack built from the commit above, task #1, nothing else running, admin user |
| | Not included | basic auth (adds ~525ms of password hashing), first request after container restart, other tasks |

Why 60ms: CVAT's own `GET /api/labels?task_id=1` takes about 55ms on my machine (see below). My endpoint basically returns the same labels with a count next to each, so it shouldn't cost much more than that. 60ms gives a bit of room for the count query and permission check. If I miss it then the counting is what's slow and I want to know that.

### Baseline before writing any code

Token auth, 3 runs of 10 requests, 22 Nov 02:45 PKT. Raw output:

```
api/server/about
  run: median=18ms min=17ms max=19ms
  run: median=18ms min=18ms max=19ms
  run: median=21ms min=20ms max=203ms
api/tasks/1
  run: median=43ms min=42ms max=51ms
  run: median=43ms min=42ms max=47ms
  run: median=42ms min=41ms max=43ms
api/labels?task_id=1&page_size=100
  run: median=55ms min=54ms max=59ms
  run: median=55ms min=54ms max=58ms
  run: median=56ms min=55ms max=57ms
```

With basic auth instead, all of these were 567-579ms.

### Result

not measured yet
