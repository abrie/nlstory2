document.addEventListener('DOMContentLoaded', () => {
  const toggleButton = document.getElementById('toggleButton');
  const issuesList = document.getElementById('issuesList');

  if (toggleButton && issuesList) {
    toggleButton.addEventListener('click', () => {
      const showAll = toggleButton.textContent.includes('Show Only Merged PR Issues');
      toggleButton.textContent = showAll ? 'Show All Issues' : 'Show Only Merged PR Issues';
      const issueItems = issuesList.getElementsByClassName('issue-item');
      for (let item of issueItems) {
        if (showAll) {
          if (item.getAttribute('data-has-merged-pr') === 'false') {
            item.style.display = 'none';
          }
        } else {
          item.style.display = 'block';
        }
      }
    });
  }
});
