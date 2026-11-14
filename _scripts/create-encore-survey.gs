/**
 * Creates a Google Form survey for the encore presentation of the
 * 1926 Miriam McFate Journal slide deck at the Poweshiek County
 * Historical Museum, Grinnell, Iowa.
 *
 * How to use:
 *   1. Go to https://script.google.com and create a New project.
 *   2. Replace the default code with this file's contents.
 *   3. Click Run (function: createEncoreSurvey) and authorize when prompted.
 *   4. Open the Execution log to get the URLs:
 *        - "Share this link" = the URL to email to your invitees.
 *        - "Edit the form here" = the URL to review/tweak the form.
 *        - "Responses spreadsheet" = where responses are tallied.
 */

function createEncoreSurvey() {
  var form = FormApp.create('Encore Presentation: 1926 Miriam McFate Travel Journal');

  form.setDescription(
    'You are invited to an encore presentation of the 1926 Miriam McFate ' +
    'Travel Journal slide show, to be held at the Poweshiek County Historical ' +
    'Museum in Grinnell, Iowa. The program will begin at 5:30 PM on a weeknight ' +
    '(Monday-Thursday) between December 1 and December 17, 2026.\n\n' +
    'Please let us know if you are interested in attending and which dates ' +
    'work for you. We will pick the date that works for the most people and ' +
    'follow up with a confirmation.'
  );

  form.setConfirmationMessage(
    'Thank you! We will email you once a date has been chosen.'
  );

  // Respondent name
  form.addTextItem()
    .setTitle('Your name')
    .setRequired(true);

  // Respondent email
  var emailItem = form.addTextItem()
    .setTitle('Your email address')
    .setRequired(true);
  emailItem.setValidation(
    FormApp.createTextValidation()
      .requireTextIsEmail()
      .setHelpText('Please enter a valid email address.')
      .build()
  );

  // Interest
  form.addMultipleChoiceItem()
    .setTitle('Are you interested in attending the encore presentation?')
    .setChoiceValues([
      'Yes, I plan to attend',
      'Maybe, depending on the date',
      'No, I am not able to attend'
    ])
    .setRequired(true);

  // Available dates (check all that apply)
  form.addCheckboxItem()
    .setTitle('Which of these dates work for you? (Program starts at 5:30 PM. Check ALL that apply.)')
    .setChoiceValues([
      'Tuesday, December 1',
      'Wednesday, December 2',
      'Thursday, December 3',
      'Monday, December 7',
      'Tuesday, December 8',
      'Wednesday, December 9',
      'Thursday, December 10',
      'Monday, December 14',
      'Tuesday, December 15',
      'Wednesday, December 16',
      'Thursday, December 17',
      'None of these dates work for me'
    ])
    .setRequired(true);

  // How many attending
  form.addMultipleChoiceItem()
    .setTitle('How many people (including yourself) would attend with you?')
    .setChoiceValues(['1', '2', '3', '4 or more'])
    .setRequired(false);

  // Comments
  form.addParagraphTextItem()
    .setTitle('Questions or comments (optional)')
    .setRequired(false);

  // Send responses to a new spreadsheet for easy tallying
  var ss = SpreadsheetApp.create('Encore Presentation Survey Responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  var shareUrl = form.getPublishedUrl();
  var editUrl = form.getEditUrl();
  var sheetUrl = ss.getUrl();

  console.log('Share this link with invitees: ' + shareUrl);
  console.log('Edit the form here: ' + editUrl);
  console.log('Responses spreadsheet: ' + sheetUrl);

  // Belt and suspenders: write the URLs into the spreadsheet itself...
  var infoSheet = ss.insertSheet('Form Links');
  infoSheet.getRange('A1:B3').setValues([
    ['Share this link with invitees:', shareUrl],
    ['Edit the form here:', editUrl],
    ['Responses spreadsheet:', sheetUrl]
  ]);
  infoSheet.autoResizeColumns(1, 2);

  // ...and email them to yourself (best effort; skip if mail is unavailable).
  try {
    MailApp.sendMail({
      to: Session.getActiveUser().getEmail(),
      subject: 'Your Encore Presentation survey links',
      body: 'Share this link with invitees:\n' + shareUrl + '\n\n' +
            'Edit the form here:\n' + editUrl + '\n\n' +
            'Responses spreadsheet:\n' + sheetUrl
    });
  } catch (e) {
    console.log('Could not send email (links are logged above and saved in the spreadsheet): ' + e);
  }
}