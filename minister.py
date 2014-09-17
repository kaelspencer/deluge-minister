#!/usr/bin/python
from datetime import datetime
from email.mime.text import MIMEText
from pprint import pformat
import click
import json
import logging
import os
import re
import smtplib
import subprocess
import StringIO

logging.basicConfig(
    format='%(asctime)-15s %(levelname)-8s %(filename)s:%(lineno)d: '
           '%(message)s',
    level=logging.WARNING)
log = logging.getLogger(__name__)
log_string = StringIO.StringIO()
log.addHandler(logging.StreamHandler(log_string))


@click.command()
@click.argument('target', type=click.Path(exists=True, file_okay=False,
                                          resolve_path=True))
@click.argument('rulefile', type=click.Path(exists=True, file_okay=True,
                                            resolve_path=True))
@click.option('-s', '--storage-file', default='minister-storage.json',
              help='The file location to store processed files so duplication '
              'doesn\'t happen in the future.')
@click.option('--email-recipient', help='Recipient\'s email address. Requires '
              'username and password options.')
@click.option('--email-username', help='Sender\'s email address. Requires '
              'password and recipient options.')
@click.option('--email-password', help='Sender\'s email password. Requires '
              'username and recipient options.')
@click.option('--email-server', default='smtp.gmail.com',
              help='SMTP email server. Default: smtp.gmail.com')
@click.option('--email-port', default=587,
              help='SMTP server port. Default: 587')
@click.option('-d', '--depth', default=0, help='How many directories to '
              'descend into. All files encountered will be added but only '
              'folders at provided depth. Default 0.')
@click.option('-v', '--verbose', count=True,
              help='Logging verbosity, -vv for very verbose.')
def minister(target, rulefile, depth, storage_file, verbose, email_username,
             email_password, email_server, email_port, email_recipient):
    if verbose == 1:
        log.setLevel(logging.INFO)
    elif verbose != 0:
        log.setLevel(logging.DEBUG)

    try:
        already_processed = load_storage_file(storage_file)
        rules = load_rules(rulefile)
        targets = iterate_input(target, depth, already_processed)
        process(targets, rules)

        save_storage_fle(storage_file,
                         [x[0] for x in targets] + already_processed)
        send_log_email(email_recipient, log_string.getvalue(), email_server,
                       email_port, email_username, email_password)
    except:
        log.exception('', exc_info=True)

    log_string.close()


def iterate_input(path, depth, already_processed):
    """Recursively iterate through the path looking for items to process.

    Recursively descend through the path. All symbolic links are ignored. All
    non-folder items are considered. Only folder items at the depth are
    considered.
    """
    result = []

    for dir in os.listdir(path):
        if not os.path.islink(dir):
            abs_path = '%s/%s' % (path, dir)
            if should_be_included(abs_path, depth == 0, already_processed):
                result.append((abs_path, os.path.isdir(abs_path)))

            if depth > 0 and os.path.isdir(abs_path):
                result.extend(iterate_input(abs_path, depth - 1))
    return result


def should_be_included(path, at_depth, already_processed):
    """Determines if the path item should be processed."""
    valid = at_depth or not os.path.isdir(path)
    return valid and path not in already_processed


def load_rules(file):
    """Load the JSON rules file and explode the data."""
    log.info('Loading rule file: {0}'.format(file))
    f = open(file, 'r')
    rules = json.loads(''.join(f.readlines()))
    f.close()

    # process assumes that both 'file' and 'folder' rules exist under rules.
    # Ensure they do. If neither exist, throw an error. Something needs to be
    # defined.
    if 'file' not in rules and 'folder' not in rules:
        raise Exception('No rules found in rules file. Looking for "file" '
                        'and/or "folder".')
    else:
        if 'file' not in rules:
            log.debug('File rules not found, adding empty ruleset.')
            rules['file'] = []
        if 'folder' not in rules:
            log.debug('Folder rules not found, adding empty ruleset.')
            rules['folder'] = []

    # Now validate that each rule has the required values.
    processed_rules = {
        'file': [],
        'folder': []
    }

    def validate_rule(rule):
        if ('match' in rule and type(rule['match']) is unicode and
                'command' in rule and type(rule['command']) is unicode):
            return True
        else:
            log.warn('Ignoring malformed rule: {0}'.format(rule))
            return False

    for rule in rules['file']:
        if validate_rule(rule):
            processed_rules['file'].append(rule)

    for rule in rules['folder']:
        if validate_rule(rule):
            processed_rules['folder'].append(rule)

    return processed_rules


def process(targets, rules):
    """Process targets using the rules.

    Iterate through the targets looking for rule matches. There should be a set
    of rules for files and another for folders.
    """
    log.info('To process:\n{0}'.format(pformat(targets)))
    log.debug('Rules:\n{0}'.format(pformat(rules)))

    for target in targets:
        typekey = 'folder' if target[1] else 'file'
        # Look for matching rules based on the type.
        for rule in rules[typekey]:
            if re.match(rule['match'], target[0]):
                log.info('Found a match: {0} with {1}, type {2}'
                         .format(target[0], rule['match'], typekey))
                cmd = rule['command'].format(target[0])
                log.info(cmd)
                log.info(subprocess.check_output(cmd.split()))


def save_storage_fle(file, processed):
    """Output the processed list to a file."""
    log.info('Write processed list: {0}'.format(file))
    log.debug('Value:\n{0}'.format(pformat(processed)))
    f = open(file, 'w')
    f.write(json.dumps(processed, sort_keys=True, indent=4,
                       separators=(',', ': ')))
    f.write('\n')
    f.close()


def load_storage_file(file):
    """Attempt to load the saved processed list.

    Load the saved file, parse the json, and return the list. If the file
    doesn't exist, catch the exception, log out a statement, and return an
    empty list.
    """
    try:
        log.info('Loading previously processed file: {0}'.format(file))
        f = open(file, 'r')
        lines = f.readlines()
        lines = json.loads(''.join(lines))
        log.debug('Value:\n{0}'.format(pformat(lines)))
        f.close()
        return lines
    except:
        log.info('Anticipated error loading processed file.', exc_info=True)
        return []


def send_log_email(recipient, body, server, port, username, password):
    """Send the log statements over email.

    The SMTP information is provided and used to send the log statements to the
    recipient. Server, username, password, and recipient must be set. If only
    some of them are set a warning is printed out.
    """
    if not server or not username or not password or not recipient:
        if username or password or recipient:
            # Username, password, and the recipient address must be supplied by
            # the user. If they supplied one and not the other print a message.
            log.warning('Not sending email. Missing parameters.')
        return

    log.info('Start sending email.')
    msg = MIMEText('<html><body><pre><code>{0}</code></pre></body></html>'
                   .format(body), 'html')
    msg['Subject'] = 'deluge-minister log at {0}'.format(
        datetime.now().isoformat())
    msg['From'] = username
    msg['To'] = recipient

    try:
        s = smtplib.SMTP(server, port)
        s.ehlo()
        s.starttls()
        s.ehlo
        s.login(username, password)
        s.sendmail(username, [recipient], msg.as_string())
        s.close()
        log.info('Finished sending email.')
    except smtplib.SMTPException:
        log.exception('Failed to send log email.', exc_info=True)

if __name__ == '__main__':
    minister()
