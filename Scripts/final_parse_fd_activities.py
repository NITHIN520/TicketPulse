import pandas as pd
import re
from datetime import datetime

INPUT_XLSX = "ticket_activities_scraped1.xlsx"
OUTPUT_XLSX = "/Users/NithinG/Desktop/ticket_activities_structured1.xlsx"

# ---------------------------------------------------
# FINAL LIST OF FRESHDESK ACTION TAGS
# ---------------------------------------------------
TAG_KEYWORDS = [
    "created a new ticket",
    "replied",
    "reported via phone",
    "reported via the portal",
    "added a private note",
    "status updated",
    "tag updated",
    "priority changed",
    "group updated",
    "agent assigned",
    "agent reassigned",
    "modified last status timestamp",
    "sent email",
    "executed an automation",
    "follow up",
    "cs eta update",
    "ticket not validated",
    "automatically reopen tickets",
]

# ---------------------------------------------------
# UI / PROFILE BLOCK FILTER (NOT REAL ACTIVITIES)
# ---------------------------------------------------
UI_NOISE_KEYWORDS = [
    "commerceiq email",
    "view more info",
    "recent tickets",
    "linked tickets",
    "parent",
    "child service tasks",
    "average handling time",
    "time logs",
    "to-do",
    "pagerduty",
    "atlassian jira",
    "plus",
]

# ---------------------------------------------------
# TIME DETECTION (ABSOLUTE ONLY)
# ---------------------------------------------------
def looks_like_time(line: str) -> bool:
    return "(" in line and " at " in line and ")" in line


def parse_absolute_time(text: str):
    m = re.search(r"\(([^)]+)\)", text)
    if not m:
        return None

    try:
        return datetime.strptime(
            m.group(1).strip(),
            "%a, %d %b %Y at %I:%M %p"
        )
    except Exception:
        return None


# ---------------------------------------------------
# ACTOR DETECTION
# ---------------------------------------------------
def is_actor_start(lines, i):
    line = lines[i]

    if line in ("System", "Customer Support"):
        return line, i + 1

    if len(line) == 1 and line.isalpha() and i + 1 < len(lines):
        name = lines[i + 1].strip()
        if name not in (
            "Reply",
            "Add note",
            "Forward",
            "Merge",
            "Child service task",
        ):
            return name, i + 2

    return None, i


# ---------------------------------------------------
# PARSE EVENTS
# ---------------------------------------------------
def parse_events_from_text(ticket_id, raw_text):
    raw_lines = [l.rstrip() for l in raw_text.splitlines()]

    # Skip UI header
    start_idx = 0
    for i, l in enumerate(raw_lines):
        if "Hide activities" in l:
            start_idx = i + 1
            break

    lines = [l.strip() for l in raw_lines[start_idx:] if l.strip()]

    rows = []
    i = 0
    last_dt = None

    while i < len(lines):
        actor, next_i = is_actor_start(lines, i)
        if not actor:
            i += 1
            continue

        i = next_i
        pre, post = [], []
        time_line = ""

        while i < len(lines):
            maybe_actor, _ = is_actor_start(lines, i)
            if maybe_actor:
                break

            line = lines[i]

            if not time_line and looks_like_time(line):
                time_line = line
            elif not time_line:
                pre.append(line)
            else:
                post.append(line)

            i += 1

        # ---------------------------------------------------
        # ACTION TAG DETECTION
        # ---------------------------------------------------
        action_tag = ""
        action_text_parts = []

        if pre and any(pre[0].lower().startswith(k) for k in TAG_KEYWORDS):
            action_tag = pre[0]
            action_text_parts = pre[1:] + post

        elif post and any(post[0].lower().startswith(k) for k in TAG_KEYWORDS):
            action_tag = post[0]
            action_text_parts = pre + post[1:]

        else:
            action_text_parts = pre + post

        action_text = " ".join(action_text_parts).strip()

        # ---------------------------------------------------
        # SKIP UI PROFILE / METADATA BLOCKS
        # ---------------------------------------------------
        lower_text = action_text.lower()
        if any(k in lower_text for k in UI_NOISE_KEYWORDS):
            continue

        # ---------------------------------------------------
        # TIME HANDLING
        # ---------------------------------------------------
        if time_line:
            dt = parse_absolute_time(time_line)
            if dt:
                last_dt = dt
        else:
            dt = last_dt

        rows.append(
            {
                "Ticket": ticket_id,
                "Actioned By": actor,
                "Action Text": action_text,
                "Action Tag": action_tag,
                "Date": dt.strftime("%a, %d %b %Y") if dt else "",
                "Time (IST)": dt.strftime("%I:%M %p") if dt else "",
            }
        )

    return rows


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    df = pd.read_excel(INPUT_XLSX, dtype=str)
    all_rows = []

    for _, r in df.iterrows():
        ticket_id = str(r.get("ticket_id", "")).strip()
        raw_text = str(r.get("activities_text", "") or "").strip()
        if ticket_id and raw_text:
            all_rows.extend(parse_events_from_text(ticket_id, raw_text))

    out_df = pd.DataFrame(all_rows)

    # ---------------------------------------------------
    # BACKFILL DATE & TIME (PANDAS 3.0 SAFE)
    # ---------------------------------------------------
    out_df.loc[:, "Date"] = (
        out_df.groupby("Ticket")["Date"]
        .transform(lambda x: x.replace("", pd.NA).bfill().ffill())
    )

    out_df.loc[:, "Time (IST)"] = (
        out_df.groupby("Ticket")["Time (IST)"]
        .transform(lambda x: x.replace("", pd.NA).bfill().ffill())
    )

    out_df.to_excel(OUTPUT_XLSX, index=False)
    print(f"✅ Parsed activities saved to {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
