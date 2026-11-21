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

### Result: missed (63.9 ms vs 60 ms target)

22 Nov 03:38 PKT, measured exactly as described above. Raw output:

```
MO-1  GET /api/annotation-counts/1  token auth  22 Nov 03:38:10 PKT
run 1: median=72.6ms min=62.7ms max=84.1ms
run 2: median=64.6ms min=59.2ms max=260.4ms
run 3: median=63.9ms min=58.9ms max=68.3ms
run 4: median=63.8ms min=58.8ms max=76.7ms
run 5: median=61.7ms min=58.7ms max=69.3ms
```

Median of the 5 runs: **63.9 ms**. Spread of the run medians: 61.7 - 72.6 ms. Fastest single request 58.7 ms, one outlier at 260 ms in run 2.

Why I missed it - timed each part inside the server (median of 20 calls, Django shell):

```
count query          13.3 ms
get_labels (80)       2.7 ms
task lookup           1.9 ms
```

So the endpoint is about 9 ms slower than /api/labels and nearly all of that is my count query. EXPLAIN ANALYZE shows most of it is sorting + aggregating all 8109 shape rows, plus ~3 ms of planning for the 3-part UNION. I tried counting the groups as a row `COUNT(DISTINCT (job_id, frame, group))` instead of the text key Django builds: 8.9 ms vs 10.9-12.3 ms execution, so maybe 2-3 ms, which is inside the noise between runs.

What would actually get it under 60 ms is caching the counts, but a cache has to be cleared every time annotations change, and the live update part (item 8) needs that same "annotations changed" hook anyway. So I'm not adding caching now. If there's time after the websocket part I'll add it on top of that hook and measure again here.
