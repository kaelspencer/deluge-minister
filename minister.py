#!/usr/bin/python
from datetime import datetime
from email.mime.text import MIMEText
from pprint import pformat
import click
import json
import logging
import os
import smtplib
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
def minister(target, depth, storage_file, verbose, email_username,
             email_password, email_server, email_port, email_recipient):
    if verbose == 1:
        log.setLevel(logging.INFO)
    elif verbose != 0:
        log.setLevel(logging.DEBUG)

    try:
        already_processed = load_storage_file(storage_file)
        targets = iterate_input(target, depth, already_processed)
        log.info('To process:\n{0}'.format(pformat(targets)))
        save_storage_fle(storage_file,
                         [x[0] for x in targets] + already_processed)
        send_log_email(email_recipient, log_string.getvalue(), email_server,
                       email_port, email_username, email_password)
    except:
        log.exception('', exc_info=True)

    log_string.close()


def iterate_input(path, depth, already_processed):
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
    valid = at_depth or not os.path.isdir(path)
    return valid and path not in already_processed


def save_storage_fle(file, processed):
    log.info('Write processed list: {0}'.format(file))
    log.debug('Value:\n{0}'.format(pformat(processed)))
    f = open(file, 'w')
    f.write(json.dumps(processed, sort_keys=True, indent=4,
                       separators=(',', ': ')))
    f.write('\n')
    f.close()


def load_storage_file(file):
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


def send_log_email(to, body, smtp_server, smtp_port, smtp_username,
                   smtp_password):
    if not smtp_server or not smtp_username or not smtp_password or not to:
        if smtp_username or smtp_password or to:
            # Username, password, and the to address must be supplied by the
            # user. If they supplied one and not the other, print a message.
            log.warning('Not sending email. Missing parameters.')
        return

    log.info('Starting email')
    msg = MIMEText('<html><body><pre><code>{0}</code></pre></body></html>'
                   .format(body), 'html')
    msg['Subject'] = 'deluge-minister log at {0}'.format(
        datetime.now().isoformat())
    msg['From'] = smtp_username
    msg['To'] = to

    try:
        s = smtplib.SMTP(smtp_server, smtp_port)
        s.ehlo()
        s.starttls()
        s.ehlo
        s.login(smtp_username, smtp_password)
        s.sendmail(smtp_username, [to], msg.as_string())
        s.close()
    except smtplib.SMTPException:
        log.exception('Failed to send log email.', exc_info=True)

if __name__ == '__main__':
    minister()
