const predictionCard = document.getElementById('prediction');
const centerPredictionSlot = predictionCard.parentElement;
const sidebarPredictionContainer = document.querySelector('#panel-right .panel-inner');

function syncPredictionPlacement(inSidebar) {
  const destination = inSidebar ? sidebarPredictionContainer : centerPredictionSlot;
  if (predictionCard.parentElement === destination) return;

  const focused = document.activeElement;
  destination.prepend(predictionCard);
  if (predictionCard.contains(focused)) {
    // Wait until the destination panel's inert state has been updated.
    queueMicrotask(() => focused.focus({preventScroll: true}));
  }
}
