# AWS EUC Service Name Changes and History

This document tracks service name changes, rebrands, and historical names for AWS End User Computing (EUC) services. This helps identify when blog posts or documentation may be referring to services by their old names.

---

## Amazon WorkSpaces Personal (formerly Amazon WorkSpaces)

**Current Name:** Amazon WorkSpaces Personal  
**Previous Names:** Amazon WorkSpaces  
**Service Type:** Virtual Desktop Infrastructure (VDI)  
**Launch Date:** November 25, 2013  
**Rename Date:** November 18, 2024

### What Changed
- **Old Name:** Amazon WorkSpaces
- **New Name:** Amazon WorkSpaces Personal
- **Service Functionality:** Unchanged - still provides persistent, user-assigned virtual desktops

### Why the Rename
The service was renamed to distinguish it from the new "Amazon WorkSpaces" service (launched November 2024) which provides pooled, non-persistent desktops for task workers.

### Impact on Content
- **Posts before November 2024** mentioning "Amazon WorkSpaces" refer to what is now "WorkSpaces Personal"
- **Posts after November 2024** need to specify "WorkSpaces Personal" vs "WorkSpaces" (pooled)
- Search terms: "workspaces personal", "workspace", "vdi", "virtual desktop", "daas", "desktop as a service"

### Related Services
- Amazon WorkSpaces (new pooled desktop service)
- Amazon WorkSpaces Applications
- Amazon WorkSpaces Thin Client
- Amazon WorkSpaces Secure Browser
- Amazon WorkSpaces Core

### Documentation
https://docs.aws.amazon.com/workspaces/

---

## Amazon WorkSpaces Applications (formerly Amazon AppStream 2.0)

**Current Name:** Amazon WorkSpaces Applications  
**Previous Names:** Amazon AppStream 2.0, Amazon AppStream  
**Service Type:** Application Streaming  
**Launch Date:** November 21, 2013  
**Rename Date:** November 18, 2024

### What Changed
- **Old Names:** Amazon AppStream 2.0, Amazon AppStream
- **New Name:** Amazon WorkSpaces Applications
- **Service Functionality:** Unchanged - still streams desktop applications to users

### Why the Rename
Rebranded to align with the WorkSpaces family of services and better reflect its purpose of streaming applications.

### Impact on Content
- **Posts mentioning "AppStream 2.0"** refer to what is now "WorkSpaces Applications"
- **Posts mentioning "AppStream" (without 2.0)** likely refer to the deprecated AppStream 1.0 (discontinued 2016)
- Search terms: "appstream", "application streaming", "workspaces applications", "app streaming"

### Historical Context
- **AppStream 1.0** (2013-2016): Original version, completely redesigned
- **AppStream 2.0** (2016-2024): Major redesign, widely adopted
- **WorkSpaces Applications** (2024-present): Rebranded version of AppStream 2.0

### Related Services
- Amazon WorkSpaces Personal
- Amazon WorkSpaces Thin Client
- Amazon DCV (streaming protocol)

### Documentation
https://docs.aws.amazon.com/appstream2/

---

## Amazon WorkSpaces Secure Browser (formerly Amazon WorkSpaces Web)

**Current Name:** Amazon WorkSpaces Secure Browser  
**Previous Names:** Amazon WorkSpaces Web  
**Service Type:** Secure Browser  
**Launch Date:** November 18, 2021  
**Rename Date:** November 18, 2024

### What Changed
- **Old Name:** Amazon WorkSpaces Web
- **New Name:** Amazon WorkSpaces Secure Browser
- **Service Functionality:** Unchanged - still provides secure browser for accessing internal web applications

### Why the Rename
Rebranded to better describe the service's purpose as a secure browser solution.

### Impact on Content
- **Posts before November 2024** mentioning "WorkSpaces Web" refer to "WorkSpaces Secure Browser"
- Search terms: "workspaces web", "workspaces secure browser", "secure browser", "web access"

### Related Services
- Amazon WorkSpaces Personal
- Amazon WorkSpaces Applications

### Documentation
https://docs.aws.amazon.com/workspaces-web/

---

## Amazon DCV (formerly WSP / NICE DCV)

**Current Name:** Amazon DCV  
**Previous Names:** WorkSpaces Streaming Protocol (WSP), NICE DCV  
**Service Type:** Streaming Protocol  
**Launch Date:** May 1, 2017  
**Rename Date:** November 18, 2024

### What Changed
- **Old Names:** WorkSpaces Streaming Protocol (WSP), NICE DCV
- **New Name:** Amazon DCV
- **Service Functionality:** Unchanged - high-performance remote display protocol

### Why the Rename
Simplified branding under the Amazon name, removing the NICE branding.

### Impact on Content
- **Posts mentioning "WSP"** refer to the WorkSpaces Streaming Protocol (now Amazon DCV)
- **Posts mentioning "NICE DCV"** refer to the same protocol under previous branding
- **Posts mentioning "PCoIP"** refer to the older Teradici protocol (still supported but WSP/DCV is preferred)
- Search terms: "dcv", "nice dcv", "wsp", "workspaces streaming protocol", "streaming protocol"

### Related Services
- Amazon WorkSpaces Personal
- Amazon WorkSpaces Applications

### Documentation
https://docs.aws.amazon.com/dcv/

---

## Amazon WorkSpaces Core (New Service)

**Current Name:** Amazon WorkSpaces Core  
**Previous Names:** None (new service)  
**Service Type:** Platform  
**Launch Date:** November 18, 2024  
**Rename Date:** N/A

### What It Is
Platform for building custom virtual desktop solutions. Provides APIs and infrastructure for creating customized VDI experiences.

### Impact on Content
- **New service** launched November 2024
- Not to be confused with "Amazon WorkSpaces" (the original service, now "WorkSpaces Personal")
- Search terms: "workspaces core", "core", "custom vdi", "platform"

### Related Services
- Amazon WorkSpaces Personal

### Documentation
https://docs.aws.amazon.com/workspaces-core/

---

## Amazon WorkSpaces Thin Client (Hardware Device)

**Current Name:** Amazon WorkSpaces Thin Client  
**Previous Names:** None (new product)  
**Service Type:** Hardware  
**Launch Date:** November 27, 2023  
**Rename Date:** N/A

### What It Is
Purpose-built thin client hardware device for accessing WorkSpaces and WorkSpaces Applications.

### Impact on Content
- **New hardware** launched November 2023
- Search terms: "thin client", "thinclient", "zero client", "workspaces thin client", "hardware"

### Related Services
- Amazon WorkSpaces Personal
- Amazon WorkSpaces Applications

### Documentation
https://docs.aws.amazon.com/workspaces-thin-client/

---

## Other EUC Services (No Renames)

### Amazon WorkDocs
**Service Type:** Document Collaboration  
**Launch Date:** January 27, 2015  
**Status:** No renames  
**Documentation:** https://docs.aws.amazon.com/workdocs/

### Amazon Chime
**Service Type:** Video Conferencing  
**Launch Date:** February 13, 2017  
**Status:** No renames  
**Documentation:** https://docs.aws.amazon.com/chime/

### Amazon Connect
**Service Type:** Contact Center  
**Launch Date:** March 28, 2017  
**Status:** No renames  
**Documentation:** https://docs.aws.amazon.com/connect/

---

## Service Families

### Amazon WorkSpaces Family
The WorkSpaces family includes all services related to end-user computing:
- **Amazon WorkSpaces Personal** - Persistent virtual desktops
- **Amazon WorkSpaces** (new) - Pooled virtual desktops
- **Amazon WorkSpaces Applications** - Application streaming
- **Amazon WorkSpaces Secure Browser** - Secure web access
- **Amazon WorkSpaces Thin Client** - Hardware device
- **Amazon WorkSpaces Core** - Custom VDI platform

### Communication & Collaboration Family
Services for communication and collaboration:
- **Amazon Chime** - Video conferencing
- **Amazon Connect** - Contact center
- **Amazon WorkDocs** - Document collaboration

---

## How to Use This Information

### When Searching for Content
1. **Check the publication date** - Posts before November 2024 use old names
2. **Use multiple search terms** - Include both old and new names
3. **Look for context clues** - "AppStream 2.0" vs "AppStream" (1.0)

### When Recommending Posts
1. **Add rename warnings** - Alert users when posts use old names
2. **Provide context** - Explain what the service was called at time of writing
3. **Link to current docs** - Always provide current documentation links

### When Answering Questions
1. **Use current names** - Always refer to services by current names
2. **Acknowledge old names** - Mention "formerly known as..." for clarity
3. **Explain changes** - Briefly explain why services were renamed

---

## Quick Reference Table

| Current Name | Previous Name(s) | Rename Date | Key Change |
|-------------|------------------|-------------|------------|
| Amazon WorkSpaces Personal | Amazon WorkSpaces | Nov 2024 | Distinguish from pooled WorkSpaces |
| Amazon WorkSpaces Applications | AppStream 2.0, AppStream | Nov 2024 | Align with WorkSpaces family |
| Amazon WorkSpaces Secure Browser | WorkSpaces Web | Nov 2024 | Better describe purpose |
| Amazon DCV | WSP, NICE DCV | Nov 2024 | Simplified branding |
| Amazon WorkSpaces Core | (new) | Nov 2024 | New platform service |
| Amazon WorkSpaces Thin Client | (new) | Nov 2023 | New hardware device |

---

## Last Updated
February 24, 2026

## Version
1.1
