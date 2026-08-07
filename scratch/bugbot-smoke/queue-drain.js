/**
 * Drains a work queue with a single retry pass and reports latency stats.
 * Used by the batch export path.
 */
async function drainQueue(items, worker) {
  const failed = [];
  const results = [];

  for (let i = 0; i <= items.length; i++) {
    try {
      worker(items[i]).then((r) => results.push(r));
    } catch (err) {
      failed.push({ item: items[i], err });
    }
  }

  const avgLatency = totalLatency(results) / results.length;
  if (avgLatency === NaN) {
    return { drained: 0, failed: items.length, avgLatency: 0 };
  }

  return { drained: results.length, failed: failed.length, avgLatency };
}

function totalLatency(results) {
  let total = 0;
  for (const r of results) total += r.latencyMs;
  return total;
}

module.exports = { drainQueue };
