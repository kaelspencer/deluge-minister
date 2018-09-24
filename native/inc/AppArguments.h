#pragma once

#include "tclap/CmdLine.h"
#include <array>

namespace AppArguments_details
{

using namespace std::literals;
using namespace TCLAP;
using std::string;

class AppArguments
{
public:
    AppArguments();

    void Parse(int argc, char* argv[]);

private:
    void Validate();

    CmdLine m_cmdLine{"Deluge Minister"s, ' ', "0.5"s};

    UnlabeledValueArg<string> m_argTarget{"target"s, "the target folder"s, true, ""s, "target folder"s};
    UnlabeledValueArg<string> m_argRulefile{"rulefile"s, "the rule file"s, true, ""s, "rule file"s};

    ValueArg<string> m_argEmailRecipient{""s, "email-recipient"s, "Recipient's email address. Requires username and password options."s, false, ""s, "recipient's address"s};
    ValueArg<string> m_argEmailUsername{""s, "email-username"s, "Sender's email address. Requires password and recipient options."s, false, ""s, "sender's username"s};
    ValueArg<string> m_argEmailPassword{""s, "email-password"s, "Sender's email password. Requires username and recipient options."s, false, ""s, "sender's password"s};
    ValueArg<string> m_argEmailServer{""s, "email-server"s, "SMTP email server."s, false, ""s, "server address"s};
    ValueArg<uint16_t> m_argEmailPort{""s, "email-port"s, "SMTP server port. Default: 587"s, false, 587, "server port"s};
    SwitchArg m_argEmailAlways{""s, "email-always"s, "Normally email is only sent when new files are detected. This flag causes an email to be sent always."s};
    SwitchArg m_argPopulate{"p"s, "populate"s, "Populate the storage file normally except the rules will be ignored."s};
    SwitchArg m_argCaseInsensitive{"i"s, "case-insensitive"s, "Regular expressions are case insensitive."s};
    ValueArg<string> m_argStorageFile{"s"s, "storage-file"s, "The file location to store processed files so duplication doesn\'t happen in the future. Default: minister-storage.json"s, false, "minister-storage.json"s, "filename"s};
    ValueArg<uint16_t> m_argDepth{"d"s, "depth"s, "How many directories to descend into. All files encountered will be added but only folders at provided depth. Default 0."s, false, 0, "depth"s};
// @click.option("-v", "--verbose", count=True, help="Logging verbosity, -vv for very verbose.")

    std::array<Arg*, 12> m_args{{
        &m_argTarget, &m_argRulefile, &m_argEmailRecipient, &m_argEmailUsername, &m_argEmailPassword,
        &m_argEmailServer, &m_argEmailPort, &m_argEmailAlways, &m_argPopulate, &m_argCaseInsensitive,
        &m_argStorageFile, &m_argDepth }};
};
}

using AppArguments_details::AppArguments;
