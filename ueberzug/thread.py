"""This module reimplements the ThreadPoolExecutor.
https://github.com/python/cpython/blob/master/Lib/concurrent/futures/thread.py

The only change is the prevention of waiting
for each thread to exit on exiting the script.
"""

import sys
import threading
import weakref
import concurrent.futures as futures
import concurrent.futures.thread as thread


class DaemonThreadPoolExecutor(futures.ThreadPoolExecutor):
    """The concurrent.futures.ThreadPoolExecutor extended by
    the prevention of waiting for each thread on exiting the script.
    """

    def _adjust_thread_count(self):
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
            if sys.version_info.major >= 3 and sys.version_info.minor >= 14:
                args = (
                    weakref.ref(self, weakref_cb),
                    self._create_worker_context(),
                    self._work_queue,
                )
            else:
                args = (
                    weakref.ref(self, weakref_cb),
                    self._work_queue,
                    self._initializer,
                    self._initargs,
                )
            t = threading.Thread(
                name=thread_name, target=thread._worker, args=args, daemon=True
            )
            t.start()
            self._threads.add(t)
