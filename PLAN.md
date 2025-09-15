# D&D Session Scheduler Bot - Design Document

## 1. Problem Statement

**Current Pain Points:**
- Manual coordination of 5 people's schedules is time-consuming
- Lack of visibility on everyone's availability leads to back-and-forth messaging
- Players sometimes forget to respond about their availability
- No centralized system for tracking who has/hasn't responded

**Solution:**
A Discord bot that automates the weekly availability polling process, tracks responses, and sends reminders to ensure timely feedback from all players.

## 2. Core Features (MVP)

### 2.1 Weekly Availability Poll
- **Frequency:** Every Monday at 10:00 AM (configurable)
- **Options:** Saturday, Sunday, Both, Neither
- **Interface:** Discord message with reaction buttons
- **Target:** Dedicated scheduling channel

### 2.2 Response Tracking
- Track which users have responded
- Display current availability status
- Show deadline for responses (e.g., Wednesday 6 PM)

### 2.3 Reminder System
- **First Reminder:** 24 hours after initial poll if no response
- **Second Reminder:** 48 hours after initial poll (final reminder)
- **Method:** Direct mention in channel + optional DM

### 2.4 Summary Report
- **When:** After deadline or when all players respond
- **Content:** 
  - Clear visualization of availability
  - Suggested session day (if consensus exists)
  - List of who can attend each day

## 3. Technical Architecture

### 3.1 Technology Stack
- **Language:** Python 3.10+
- **Discord Library:** discord.py 2.x
- **Database:** SQLite (for MVP, easily portable)
- **Hosting:** Local machine initially, then migrate to cloud (Heroku free tier, Railway, or VPS)

### 3.2 Database Schema

```sql
-- Active polls
CREATE TABLE polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE,
    channel_id TEXT,
    created_at TIMESTAMP,
    deadline TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- User responses
CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER,
    user_id TEXT,
    user_name TEXT,
    saturday BOOLEAN DEFAULT 0,
    sunday BOOLEAN DEFAULT 0,
    responded_at TIMESTAMP,
    FOREIGN KEY (poll_id) REFERENCES polls(id),
    UNIQUE(poll_id, user_id)
);

-- Configuration
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### 3.3 Bot Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/schedule init` | Set up scheduling in current channel | Admin |
| `/schedule now` | Trigger immediate availability poll | Admin |
| `/schedule status` | Show current week's responses | Everyone |
| `/schedule config` | Configure poll time, deadline, etc. | Admin |

## 4. User Flow

### 4.1 Weekly Poll Flow
1. Bot posts availability message with emoji reactions:
   - 📅 = Both days
   - 🇸 = Saturday only
   - ☀️ = Sunday only
   - ❌ = Neither day
2. Players click reactions to indicate availability
3. Bot updates the message to show who has responded (checkmarks)
4. Non-responders get reminded at intervals

### 4.2 Response Message Format
```
📊 **D&D Session Availability - Week of [DATE]**

Please react with your availability for this weekend:
📅 Both days | 🇸 Saturday | ☀️ Sunday | ❌ Neither

**Deadline:** Wednesday 6:00 PM

**Responses:**
✅ Player1
✅ Player2
⏳ Player3
⏳ Player4
⏳ DM

*Reminders will be sent to pending players.*
```

### 4.3 Summary Message Format
```
📋 **Availability Summary - Week of [DATE]**

**Saturday:** Player1, Player2, DM (3/5)
**Sunday:** Player1, Player3, Player4, DM (4/5)

🎯 **Recommendation:** Sunday has better availability!
```

## 5. Implementation Phases

### Phase 1: Core Bot Setup (Week 1)
- [ ] Discord bot creation and basic setup
- [ ] Database initialization
- [ ] Basic command structure
- [ ] Configuration system

### Phase 2: Polling System (Week 1-2)
- [ ] Create availability poll message
- [ ] Handle reaction events
- [ ] Store responses in database
- [ ] Update message with response status

### Phase 3: Reminder System (Week 2)
- [ ] Implement reminder scheduling
- [ ] Add mention notifications
- [ ] Track reminder count per user

### Phase 4: Reporting (Week 2-3)
- [ ] Generate summary reports
- [ ] Add status command
- [ ] Implement recommendation logic

### Phase 5: Polish & Testing (Week 3)
- [ ] Error handling
- [ ] Logging system
- [ ] User testing with group
- [ ] Documentation

## 6. Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `poll_day` | Monday | Day to send weekly poll |
| `poll_time` | 10:00 AM | Time to send poll |
| `deadline_day` | Wednesday | Day responses are due |
| `deadline_time` | 6:00 PM | Time responses are due |
| `reminder_intervals` | [24, 48] | Hours after poll to send reminders |
| `min_players` | 3 | Minimum players for session |
| `scheduling_channel` | None | Channel ID for polls |
| `player_role` | @Player | Role to ping for polls |

## 7. Edge Cases & Handling

### 7.1 Technical Issues
- **Bot offline during scheduled poll:** Queue system to catch up
- **Reactions removed:** Update database accordingly
- **Multiple reactions:** Take most recent reaction only

### 7.2 User Issues
- **New player joins:** Admin command to add to player list
- **Player leaves:** Admin command to remove from tracking
- **Vacation/extended absence:** `/schedule skip @player [weeks]` command

## 8. Future Enhancements (Post-MVP)

### Near-term
- DM availability weighting (2x importance)
- Historical attendance tracking
- Integration with calendar apps
- Custom day selection beyond weekends

### Long-term
- Session notes and recap storage
- Character sheet quick references
- Dice rolling integration
- Campaign timeline tracking
- Multi-group support

## 9. Success Metrics

- **Response Rate:** >80% within 24 hours
- **Time Saved:** <5 minutes total coordination time per week
- **User Satisfaction:** Positive feedback from all group members
- **Reliability:** 99% uptime for scheduled polls

## 10. Security & Privacy

- No storage of message content (only IDs)
- User IDs stored, not personal information
- Admin-only configuration commands
- Rate limiting on commands
- Graceful error handling to prevent crashes

## 11. Development Environment Setup

```bash
# Required packages
discord.py>=2.0.0
python-dotenv  # for environment variables
apscheduler    # for scheduling tasks
sqlite3        # included with Python

# Environment variables (.env file)
DISCORD_TOKEN=your_bot_token_here
DEFAULT_CHANNEL_ID=channel_id_here
ADMIN_USER_IDS=comma,separated,ids
```

## 12. Testing Checklist

- [ ] Poll creates successfully
- [ ] All reaction types handled correctly
- [ ] Reminders sent at correct intervals
- [ ] Summary generates with correct data
- [ ] Configuration changes persist
- [ ] Bot recovers from disconnection
- [ ] Edge cases handled gracefully

---

**Document Version:** 1.0 (MVP)  
**Last Updated:** [Current Date]  
**Next Review:** After MVP deployment