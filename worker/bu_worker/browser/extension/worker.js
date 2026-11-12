const WORKER_BASE = "http://127.0.0.1:8090";

async function poll() {
  try {
    const response = await fetch(`${WORKER_BASE}/extension/next`, {cache: "no-store"});
    if (!response.ok) return;
    const {job} = await response.json();
    if (!job) return;

    const state = await chrome.storage.local.get("currentJob");
    if (state.currentJob && state.currentJob.id === job.id) return;

    await chrome.storage.local.set({currentJob: job});
    const tabs = await chrome.tabs.query({windowType: "normal"});
    const tab = tabs.find((item) => item.active) || tabs[0];
    if (tab && tab.id !== undefined) {
      await chrome.tabs.update(tab.id, {url: job.url, active: true});
    } else {
      await chrome.tabs.create({url: job.url, active: true});
    }
  } catch (_) {
    // FastAPI starts alongside Chromium and may briefly be unavailable.
  }
}

async function submitPage(message) {
  const response = await fetch(`${WORKER_BASE}/extension/result`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      job_id: message.jobId,
      html: message.html,
      final_url: message.finalUrl
    })
  });
  const result = response.ok ? await response.json() : {complete: false};
  if (result.complete) await chrome.storage.local.remove("currentJob");
  return result;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "pageResult") return false;
  submitPage(message).then(sendResponse).catch(() => sendResponse({complete: false}));
  return true;
});

chrome.runtime.onInstalled.addListener(poll);
chrome.runtime.onStartup.addListener(poll);
chrome.alarms.create("worker-poll", {periodInMinutes: 0.5});
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "worker-poll") poll();
});
setInterval(poll, 1000);
poll();
