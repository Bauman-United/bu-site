function capturePage() {
  chrome.storage.local.get("currentJob").then(({currentJob}) => {
    if (!currentJob) return;
    chrome.runtime.sendMessage({
      type: "pageResult",
      jobId: currentJob.id,
      html: document.documentElement.outerHTML,
      finalUrl: window.location.href
    }).catch(() => {});
  });
}

// SafeLine mutates the document after DOMContentLoaded. Multiple snapshots let
// the worker see both a late challenge and the page produced after a manual
// confirmation, without attaching a debugger to Chromium.
capturePage();
setInterval(capturePage, 1500);
