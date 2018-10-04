#!/usr/bin/python
"""Deluge Minister monitors a folder and runs command on new items."""

from datetime import datetime
from email.mime.text import MIMEText
from pprint import pformat
import click
import json
import logging
import logging.handlers
import os
import re
import shlex
import smtplib
import subprocess
import io

logging.basicConfig(
    format='%(asctime)-15s %(levelname)-8s %(filename)s:%(lineno)d: %(message)s',
    level=logging.WARNING)
log = logging.getLogger(__name__)
log_string = io.StringIO()
log.addHandler(logging.StreamHandler(log_string))
log.addHandler(logging.handlers.RotatingFileHandler('logs/minister.log', maxBytes=10485760, backupCount=10))


@click.command()
@click.argument('target', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.argument('rulefile', type=click.Path(exists=True, file_okay=True, resolve_path=True))
@click.option('-s', '--storage-file', default='minister-storage.json',
              help='The file location to store processed files so duplication doesn\'t happen in the future.')
@click.option('--email-recipient', help='Recipient\'s email address. Requires username and password options.')
@click.option('--email-username', help='Sender\'s email address. Requires password and recipient options.')
@click.option('--email-password', help='Sender\'s email password. Requires username and recipient options.')
@click.option('--email-server', default='smtp.gmail.com', help='SMTP email server. Default: smtp.gmail.com')
@click.option('--email-port', default=587, help='SMTP server port. Default: 587')
@click.option('--email-always', is_flag=True,
              help='Normally email is only sent when new files are detected. This flag causes an email to be sent always.')
@click.option('-d', '--depth', default=0,
              help='How many directories to descend into. All files encountered will be added but only folders at provided depth. Default 0.')
@click.option('--populate', is_flag=True, help='Populate the storage file normally except the rules will be ignored.')
@click.option('--case-insensitive', is_flag=True, help='Regular expressions are case insensitive.')
@click.option('-v', '--verbose', count=True, help='Logging verbosity, -vv for very verbose.')
def minister(target, rulefile, depth, storage_file, verbose, email_username, email_password, email_server, email_port,
             email_recipient, populate, email_always, case_insensitive):
    """Kick off the minister work."""
    if verbose == 1:
        log.setLevel(logging.INFO)
    elif verbose != 0:
        log.setLevel(logging.DEBUG)

    mailer = LogEmailer(email_username, email_password, email_server, email_port)
    minstr = Minister(depth, populate, case_insensitive)
    minstr.run(target, rulefile, storage_file)
    minstr.sendmail(mailer, email_recipient, email_always)

    log_string.close()


class LogEmailer(object):
    """A class to email the log file."""
    def __init__(self, username, password, server, port):
        self.username = username
        self.password = password
        self.server = server
        self.port = port


    def send(self, recipient, summary, body):
        """Send the log statements over email.

        The SMTP information is provided and used to send the log statements to
        the recipient. Server, username, password, and recipient must be set.
        If only some of them are set a warning is printed out.
        """
        if not self.valid(recipient):
            return

        log.info('Start sending email.')
        fmt = u'<html><body><pre><code>{0}<br/><br/>{1}</code></pre></body></html>'
        msg = MIMEText(fmt.format(summary, body), 'html', _charset="UTF-8")
        msg['Subject'] = 'deluge-minister log at {0}'.format(datetime.now().isoformat())
        msg['From'] = self.username
        msg['To'] = recipient

        try:
            smtp = smtplib.SMTP(self.server, self.port)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.username, self.password)
            smtp.sendmail(self.username, [recipient], msg.as_string())
            smtp.close()
            log.info('Finished sending email.')
        except smtplib.SMTPException:
            log.exception('Failed to send log email.', exc_info=True)

    def valid(self, recipient):
        """Determines if the class has the proper values to send an email."""
        if not self.server or not self.username or not self.password or not recipient:
            if self.username or self.password or recipient:
                # Nothing being supplied means don't send the email. A subset
                # being supplied is an error case.
                log.error('Not sending email. Missing parameters.')
            return False
        return True


class Minister(object):
    """The minister object."""
    def __init__(self, depth, populate, case_insensitive):
        self.depth = depth
        self.populate = populate
        self.case_insensitive = case_insensitive

        self.processed = []
        self.unprocessed = []

        self.rules = {
            'rules': {'file': [], 'folder': []},
            'ignore': {'file': [], 'folder': []},
            'onComplete': {'command': [], 'onlyAfterMatch': True}
        }


    def run(self, target, rulefile, storage):
        """Start the minister work."""
        try:
            already_processed = self.load_storage_file(storage)

            # If the populate flag is set, don't load the rule file. This will cause all files to be
            # added to the output file.
            if not self.populate:
                self.load_rules(rulefile)

            targets = self.iterate_input(target, self.depth, already_processed)
            self.processed, self.unprocessed = self.process(targets, self.rules, self.case_insensitive)
            self.on_complete()

            self.save_storage_fle(storage, [x[0] for x in targets] + already_processed)
        except:
            log.exception('', exc_info=True)


    def sendmail(self, mailer, recipient, always):
        """Send the log mail.

        The LogMailer object is provided. always causes minister to always send
        a status mail even if nothing was processed.
        """
        summary = self.summarize(self.processed, self.unprocessed)
        if always or len(self.processed) > 0 or len(self.unprocessed) > 0:
            mailer.send(recipient, summary, log_string.getvalue())


    def iterate_input(self, path, depth, already_processed):
        """Recursively iterate through the path looking for items to process.

        Recursively descend through the path. All symbolic links are ignored.
        All non-folder items are considered. Only folder items at the depth are
        considered.
        """
        result = []

        for subdir in os.listdir(path):
            if os.path.islink(subdir):
                continue

            abs_path = '%s/%s' % (path, subdir)
            isdir = os.path.isdir(abs_path)

            if self.should_be_included(abs_path, depth == 0, already_processed):
                result.append((abs_path, isdir))

            if depth > 0 and isdir and not self.should_ignore(abs_path, isdir):
                result.extend(self.iterate_input(abs_path, depth - 1, already_processed))
        return result


    def should_be_included(self, path, at_depth, already_processed):
        """Determines if the path item should be processed."""
        isdir = os.path.isdir(path)
        return (at_depth or not isdir) \
            and path not in already_processed \
            and not self.should_ignore(path, isdir)


    def should_ignore(self, path, isdir):
        """Determines if the path should be ignored."""
        typekey = 'folder' if isdir else 'file'
        for ign in self.rules['ignore'][typekey]:
            if re.match(ign, path):
                log.debug(u'Ignoring {0}, matched ignore rule {1}'.format(path, ign))
                return True
        return False


    def rule_has_command(self, rule):
        """Determine if a rule has a valid command."""
        valid = True

        if 'command' in rule and type(rule['command']) is str:
            # The rules file has a string for a command. Normalize it into an array.
            rule['command'] = [rule['command']]
        elif 'command' in rule and type(rule['command']) is list and len(rule['command']) > 0:
            # The rules file has an array. Ensure all elements are strings.
            for cmd in rule['command']:
                if type(cmd) is not str:
                    valid = False
                    break
        else:
            valid = False

        return valid


    def load_rules(self, filepath):
        """Load the JSON rules file and explode the data."""
        # Now validate that each rule has the required values.

        log.info('Loading rule file: {0}'.format(filepath))
        rulefile = open(filepath, 'r')
        full = json.loads(''.join(rulefile.readlines()))
        rulefile.close()

        if 'rules' not in full:
            raise Exception('No rules found in rules file. Looking for top level "rules".')
        rules = full['rules']

        # process assumes that both 'file' and 'folder' rules exist under
        # rules. Ensure they do. If neither exist, throw an error. Something
        # needs to be defined.
        if 'file' not in rules and 'folder' not in rules:
            raise Exception('No rules found in rules file. Looking for "file" and/or "folder".')
        else:
            for typekey in ['file', 'folder']:
                if typekey not in rules:
                    log.debug('{0} rules not found, adding empty ruleset.'.format(typekey))
                    rules[typekey] = []

        def validate_ignore(ignore):
            """Returns false for empty or non-strings."""
            return type(ignore) == str and len(ignore) > 0

        def validate_rule(rule):
            """Returns false if the rule is invalid."""
            valid = self.rule_has_command(rule)

            if 'match' not in rule or type(rule['match']) is not str:
                valid = False

            if not valid:
                log.info('Ignoring malformed rule: {0}'.format(rule))

            return valid

        # No need to ensure onComplete exists, it's optional.
        if 'onComplete' in full:
            oncomplete = full['onComplete']
            if self.rule_has_command(oncomplete):
                self.rules['onComplete']['command'] = oncomplete['command']

                if 'onlyAfterMatch' in oncomplete and type(oncomplete['onlyAfterMatch']) is bool:
                    self.rules['onComplete']['onlyAfterMatch'] = oncomplete['onlyAfterMatch']
                else:
                    self.rules['onComplete']['onlyAfterMatch'] = True
                    log.info('Malformed onComplete.onlyAfterMatch, defaulting to True.')
            else:
                # Leave self.rules['onComplete'] in the default state.
                log.info('Ignoring malformed rule for onComplete.')

        # No need to ensure any ignore list exists, it's optional.
        ignore = full['ignore'] if 'ignore' in full else {}
        for typekey in ['file', 'folder']:
            if typekey not in ignore:
                ignore[typekey] = []

        self.rules['rules']['file'] = [x for x in rules['file'] if validate_rule(x)]
        self.rules['rules']['folder'] = [x for x in rules['folder'] if validate_rule(x)]
        self.rules['ignore']['file'] = [x for x in ignore['file'] if validate_ignore(x)]
        self.rules['ignore']['folder'] = [x for x in ignore['folder'] if validate_ignore(x)]


    def process(self, targets, rules, case_insensitive):
        """Process targets using the rules.

        Iterate through the targets looking for rule matches. There should be a
        set of rules for files and another for folders.
        """
        log.info('To process:\n{0}'.format(pformat(targets)))
        log.debug('Rules:\n{0}'.format(pformat(rules)))

        processed = []
        unprocessed = []
        flags = re.IGNORECASE if case_insensitive else 0

        def format_cmd(cmd, target, regex_matched_dict):
            """Format the command depending on the target type."""
            path = u'"{0}"'.format(target[0])

            if target[1]:
                # If it is a directory.
                return cmd.format(path=path)
            else:
                # Else, it's a file.
                filepath = u'{0}'.format(os.path.basename(target[0]))
                return cmd.format(path=path, file=filepath, **regex_matched_dict)

        for target in targets:
            matched = False
            try:
                typekey = 'folder' if target[1] else 'file'
                output = '\n'

                # Look for matching rules based on the type.
                for rule in rules['rules'][typekey]:
                    match = re.match(rule['match'], target[0], flags)
                    if match is not None:
                        log.info(u'Found a match: {0} with {1}, type {2}'.format(target[0], rule['match'], typekey))
                        for cmd in rule['command']:
                            cmd = format_cmd(cmd, target, match.groupdict())
                            output += '> ' + cmd + '\n'
                            output += subprocess.check_output(shlex.split(cmd)).decode('utf-8')
                        matched = True
                        break
            except subprocess.CalledProcessError as err:
                log.error('Command failed.\nCommand: {0}\nOutput: {1}'.format(err.cmd, err.output))
                log.warning('Output buffer:\n{0}'.format(output))
                log.exception('', exc_info=True)
            except KeyError as err:
                # Failed to format the command.
                log.error('Formatting command failed. Typo in named groups?')
                log.warning('Output buffer:\n{0}'.format(output))
                log.exception('', exc_info=True)
            except:
                log.warning('Output buffer:\n{0}'.format(output))
                log.exception('', exc_info=True)

            if matched:
                log.warning(output)
                processed.append(target)
            else:
                unprocessed.append(target)

        return processed, unprocessed


    def summarize(self, processed, unprocessed):
        """Output a summary of processed and unprocessed targets."""
        summary = 'Summary:\nProcessed:\n\t'

        processed.sort()
        unprocessed.sort()

        if len(processed):
            summary += '\n\t'.join([x[0] for x in processed])
        else:
            summary += 'None'

        summary += '\n\nUnmatched:\n\t'

        if len(unprocessed):
            summary += '\n\t'.join([x[0] for x in unprocessed])
        else:
            summary += 'None'

        log.warning(summary)
        return summary


    def save_storage_fle(self, filepath, processed):
        """Output the processed list to a file."""
        log.info('Write processed list: {0}'.format(filepath))
        log.debug('Value:\n{0}'.format(pformat(processed)))
        with open(filepath, 'w') as storagefile:
            storagefile.write(json.dumps(processed, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=False))
            storagefile.write('\n')


    def load_storage_file(self, filepath):
        """Attempt to load the saved processed list.

        Load the saved file, parse the json, and return the list. If the file
        doesn't exist, catch the exception, log out a statement, and return an
        empty list.
        """
        try:
            log.info('Loading previously processed file: {0}'.format(filepath))
            with open(filepath, 'r') as storagefile:
                lines = storagefile.readlines()
                lines = json.loads(''.join(lines))
                log.debug('Value:\n{0}'.format(pformat(lines)))
            return lines
        except IOError:
            log.debug('Anticipated error loading processed file.', exc_info=True)
            return []


    def on_complete(self):
        """Run the onComplete commands if necessary."""
        onlyaftermatch = self.rules['onComplete']['onlyAfterMatch']

        # Only process the onComplete if the flag says to run it always or if there are processed items.
        if not onlyaftermatch or len(self.processed) > 0:
            try:
                output = '\n'

                for cmd in self.rules['onComplete']['command']:
                    output += '> ' + cmd + '\n'
                    output += subprocess.check_output(shlex.split(cmd)).decode('utf-8')
            except subprocess.CalledProcessError as err:
                log.error('Command failed.\nCommand: {0}\nOutput: {1}'.format(err.cmd, err.output))
                log.warning('Output buffer:\n{0}'.format(output))
                log.exception('', exc_info=True)
            except (OSError, UnicodeDecodeError):
                log.warning('Output buffer:\n{0}'.format(output))
                log.exception('', exc_info=True)

            log.warning(output)


if __name__ == '__main__':
    minister()
