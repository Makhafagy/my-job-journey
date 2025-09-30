function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Apply Tracker')
    .addItem('Add Applied Column', 'ensureAppliedColumn')
    .addToUi();
}

function ensureAppliedColumn() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  let col = headers.indexOf("Applied") + 1;

  if (col === 0) {
    col = sheet.getLastColumn() + 1;
    sheet.getRange(1, col).setValue("Applied");
  }

  // Set all cells in Applied column to checkbox
  sheet.getRange(2, col, sheet.getLastRow() - 1).insertCheckboxes();
  SpreadsheetApp.getUi().alert('"Applied" column ready with checkboxes!');
}

// Triggered automatically on any edit
function onEdit(e) {
  const sheet = e.range.getSheet();
  const row = e.range.getRow();
  const col = e.range.getColumn();
  
  // Ignore header
  if (row === 1) return;

  // Find "Applied" column
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const appliedCol = headers.indexOf("Applied") + 1;
  if (appliedCol === 0) return;

  if (col === appliedCol) {
    const value = e.range.getValue();
    const rowRange = sheet.getRange(row, 1, 1, sheet.getLastColumn());
    if (value === true) {
      rowRange.setBackground('#d4f4dd'); // light green
    } else {
      rowRange.setBackground(null); // remove highlight if unchecked
    }
  }
}
