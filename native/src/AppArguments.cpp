#include "AppArguments.h"

// using namespace std::literals;
using namespace TCLAP;
using namespace std;

AppArguments::AppArguments()
{
    for (const auto& arg : m_args)
    {
        m_cmdLine.add(arg);
    }
}

void AppArguments::Parse(int argc, char* argv[])
{
    m_cmdLine.parse(argc, argv);
    Validate();
}

void AppArguments::Validate()
{
    const array<bool, 4> emailArgsSet{{
        !m_argEmailRecipient.getValue().empty(),
        !m_argEmailUsername.getValue().empty(),
        !m_argEmailPassword.getValue().empty(),
        !m_argEmailServer.getValue().empty()}};

    const bool allEmailArgsSet = all_of(emailArgsSet.begin(), emailArgsSet.end(), bind(equal_to<bool>(), true, placeholders::_1));
    const bool noEmailArgsSet = all_of(emailArgsSet.begin(), emailArgsSet.end(), bind(equal_to<bool>(), false, placeholders::_1));
    // !always && none || all || always && all
    const bool emailValid = (!m_argEmailAlways.getValue() && noEmailArgsSet) || (allEmailArgsSet) || (m_argEmailAlways.getValue() && allEmailArgsSet);
    const bool emailEnabled = emailValid && allEmailArgsSet;

    cout << boolalpha << "Email valid: " << emailValid << " - Email enabled: " << emailEnabled << "\n";
}
