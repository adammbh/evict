const Privacy = () => {
    return (
        <div className="flex flex-col mx-[10vw] mt-5 sm:mx-[25vw]">
            <span className="font-bold text-5xl text-white">Privacy Policy</span>
            <span className="text-evict-pink italic text-sm mt-5">
                Last updated And Effective Since: 2025-01-08 (8th of January 2025)
            </span>
            <span className="text-neutral-400 text-sm mt-5 pb-5">
                Any information we collect is not used in any malicious manner. If anything shown
                seems misleading, please contact us @{" "}
                <span className="text-white font-semibold">support@evict.bot</span>
            </span>
            <div className="flex flex-col gap-4 text-[17px] pl-5">
                <li className="text-neutral-400 marker:text-evict-pink">Guild IDs</li>
                <li className="text-neutral-400 marker:text-evict-pink">Guild Names</li>
                <li className="text-neutral-400 marker:text-evict-pink">Channel IDs</li>
                <li className="text-neutral-400 marker:text-evict-pink">Role IDs</li>
                <li className="text-neutral-400 marker:text-evict-pink">User IDs</li>
                <li className="text-neutral-400 marker:text-evict-pink">Message Timestamps</li>
                <li className="text-neutral-400 marker:text-evict-pink">Message IDs</li>
                <li className="text-neutral-400 marker:text-evict-pink">Past Avatars</li>
                <li className="text-neutral-400 marker:text-evict-pink">Nicknames and Usernames</li>
                <li className="text-neutral-400 marker:text-evict-pink">
                    Message content when a command is ran (stored for a max of 14 days) or when
                    arguments are passed for commands
                </li>
                <li className="text-neutral-400 marker:text-evict-pink">
                    Last deleted message content (stored for a max of 2 hours or less)
                </li>
                <li className="text-neutral-400 marker:text-evict-pink">
                    Last message edit history (stored for a max of 2 hours or less)
                </li>
                <li className="text-neutral-400 marker:text-evict-pink">
                    Last Emoji Reaction History (stored for a max of 2 hours or less)
                </li>
            </div>
            <span className="font-bold text-2xl text-white pt-10">
                Analytics and Performance Monitoring
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                We collect anonymous usage data and performance metrics to improve our service quality and user experience. This includes:
            </span>
            <div className="flex flex-col gap-4 text-[17px] pl-5">
                <li className="text-neutral-400 marker:text-evict-pink">Command usage statistics and patterns</li>
                <li className="text-neutral-400 marker:text-evict-pink">Bot performance metrics (response times, system resource usage)</li>
                <li className="text-neutral-400 marker:text-evict-pink">Feature adoption rates</li>
                <li className="text-neutral-400 marker:text-evict-pink">Error tracking and debugging information</li>
                <li className="text-neutral-400 marker:text-evict-pink">User interaction patterns with bot features</li>
                <li className="text-neutral-400 marker:text-evict-pink">Server growth and activity metrics</li>
                <li className="text-neutral-400 marker:text-evict-pink">Security incident detection and prevention data</li>
                <li className="text-neutral-400 marker:text-evict-pink">Bot configuration changes</li>
                <li className="text-neutral-400 marker:text-evict-pink">Command success/failure rates</li>
            </div>
            <span className="text-neutral-400 text-sm mt-5">
                This data is processed and stored using PostHog analytics platform. The data is hosted on our servers in Dallas, Texas. We collect this information to:
            </span>
            <div className="flex flex-col gap-4 text-[17px] pl-5">
                <li className="text-neutral-400 marker:text-evict-pink">Improve bot performance and reliability</li>
                <li className="text-neutral-400 marker:text-evict-pink">Identify and fix bugs</li>
                <li className="text-neutral-400 marker:text-evict-pink">Optimize popular features</li>
                <li className="text-neutral-400 marker:text-evict-pink">Detect and prevent abuse</li>
                <li className="text-neutral-400 marker:text-evict-pink">Make data-driven decisions about new features</li>
                <li className="text-neutral-400 marker:text-evict-pink">Monitor system health and resource usage</li>
            </div>
            <span className="text-neutral-400 text-sm mt-5">
                The analytics data is:
            </span>
            <div className="flex flex-col gap-4 text-[17px] pl-5">
                <li className="text-neutral-400 marker:text-evict-pink">Pseudonymized (no personally identifiable information)</li>
                <li className="text-neutral-400 marker:text-evict-pink">Stored securely with restricted access</li>
                <li className="text-neutral-400 marker:text-evict-pink">Retained for a maximum of 30 days</li>
                <li className="text-neutral-400 marker:text-evict-pink">Never sold or shared with third parties</li>
                <li className="text-neutral-400 marker:text-evict-pink">Used solely for improving our service</li>
            </div>
            <span className="text-neutral-400 text-sm mt-5">
                You can request information about what analytics data we store by contacting support@evict.bot. While we cannot opt out individual users from analytics collection as it&apos;s essential for service operation and security, we minimize the data collected to only what&apos;s necessary for these purposes.
            </span>
            <span className="font-bold text-2xl text-white pt-10">
                Why do we need the data and how is it used?
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                When a command is invoked, we store the message content for a maximum of 14 days for
                debugging purposes. We also store a maximum of 18 entries for edited messages and
                sniping messages that will expire in two hours or less in volatile memory.
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                Guild IDs, Channel IDs, Role IDs, User IDs and Message IDs are all stored for our
                system to aggregate values to find data.
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                Nickname, Username and Avatar changes are logged in order for the
                &quot;namehistory&quot; and &quot;avatarhistory&quot; commands to function. Users
                can clear this data themselves at any time.
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                Guild name changes are logged in order for the &quot;gnames&quot; command to
                function. Server administrators can clear this data themselves at any time.
            </span>
            <span className="font-bold text-2xl text-white pt-10">
                Who is your collected information shared with?
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                We do not sell or expose your information to others, and, or third parties.
            </span>
            <span className="font-bold text-2xl text-white pt-10">Data Removal?</span>
            <span className="text-neutral-400 text-sm mt-5">
                Email <span className="text-white font-semibold">support@evict.bot</span> for all of
                your data that we are currently storing. Response times may vary and could take up
                to 7 days.
            </span>
            <span className="font-bold text-2xl text-white pt-10">Data Storage and Backups</span>
            <span className="text-neutral-400 text-sm mt-5">
                Our primary data storage is located in Dallas, Texas. For redundancy and disaster
                recovery, we maintain replicated backups across data centers in New York, USA and
                Falkenstein, Germany.
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                We perform automated backups every 8 hours (3 times daily) in UTC timezone. These backups
                are retained for 7 days before being permanently deleted. While we will honor data deletion 
                requests for our active systems, please note that we may be unable to remove your data from 
                existing backups until they expire naturally from our retention cycle.
            </span>
            <span className="font-bold text-2xl text-white pt-10">
                Changes to the Privacy Policy
            </span>
            <span className="text-neutral-400 text-sm mt-5">
                We can update these terms at any time without notice. Continuing to use our services
                after any changes will mean that you agree with these terms and violation of our
                terms of service could result in a permanent ban across all of our services.
            </span>
        </div>
    )
}

export default Privacy
