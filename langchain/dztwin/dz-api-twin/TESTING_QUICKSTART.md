# Testing Quick Start Guide

Get started with manual testing in 5 minutes!

---

## 🚀 Step 1: Verify Environment (2 minutes)

```bash
# Run the pre-test verification script
cd backend
python pre_test_check.py
```

**Expected Output**: All checks should pass ✓

If any checks fail, fix them before proceeding.

---

## 🚀 Step 2: Start All Services (1 minute)

### Terminal 1: Backend
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python main.py
```

**Wait for**: `Application startup complete` + `RAG service initialized`

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

**Wait for**: `Server running on http://localhost:8000`

### Terminal 3: Verify Qdrant
```bash
finch ps
```

**Expected**: `qdrant` container should be running

---

## 🚀 Step 3: Open Test Page (30 seconds)

1. Open browser: **http://localhost:8000/example.html**
2. Open DevTools: **F12** or **Cmd+Option+I** (Mac)
3. Switch to **Console** tab (watch for errors)
4. Switch to **Network** tab (monitor API calls)

---

## 🚀 Step 4: First Test - Basic Chat (1 minute)

### Test 1: Widget Opens
1. Click the **blue FAB** (floating button) in bottom-right
2. Widget should slide up smoothly
3. You should see the chat interface

✅ **Pass**: Widget opens  
❌ **Fail**: Check console for errors

### Test 2: Send First Message
1. Type: `"Hello, can you help me?"`
2. Press **Enter** or click **Send**
3. Watch for response

✅ **Pass**: AI responds  
❌ **Fail**: Check Network tab for failed requests

---

## 🚀 Step 5: First RAG Test (1 minute)

### Test 3: Documentation Query
1. Send: `"How do I authenticate with the API?"`
2. Wait for response
3. Check backend terminal for logs

**Backend logs should show**:
```
RAG search query: How do I authenticate with the API?
Found 5 relevant documents
Document scores: [0.85, 0.82, ...]
```

**Response should include**:
- Specific authentication information from your docs
- Code examples (if available)
- Source links at the bottom

✅ **Pass**: Response includes doc-specific info + sources  
❌ **Fail**: Response is generic (RAG not working)

---

## 🎯 Quick Test Checklist (5 minutes)

Run through these quickly to verify everything works:

### Basic Functionality
- [ ] Widget opens and closes smoothly
- [ ] Can send messages
- [ ] AI responds with streaming
- [ ] Markdown renders (code blocks, lists, etc.)
- [ ] Can scroll through messages

### RAG Functionality
- [ ] Documentation queries get specific answers
- [ ] Sources are displayed at bottom
- [ ] Backend logs show RAG retrieval
- [ ] Relevance scores are > 0.7
- [ ] Multiple sources cited (2-5)

### UI/UX
- [ ] Typing indicator shows while waiting
- [ ] Auto-scrolls to new messages
- [ ] Textarea resizes with content
- [ ] No console errors
- [ ] No visual glitches

---

## 🐛 Quick Troubleshooting

### Problem: Widget doesn't open
**Check**:
- Console for JavaScript errors
- Network tab for failed requests
- Frontend server is running on port 8000

### Problem: No AI response
**Check**:
- Backend is running on port 3000
- Network tab shows request to `/api/chat`
- Backend logs for errors
- AWS credentials are configured

### Problem: Generic responses (RAG not working)
**Check**:
- Backend logs show "RAG service initialized"
- Qdrant is running: `finch ps`
- Collection has documents: `python -c "from qdrant_client import QdrantClient; print(QdrantClient(url='http://localhost:6333').get_collection('api_docs').vectors_count)"`
- `.env` has `RAG_ENABLED=true`

### Problem: Sources not displayed
**Check**:
- Backend logs show documents retrieved
- Response includes source URLs
- Frontend is rendering markdown correctly

---

## 📊 What to Test Next

After the quick start, proceed with:

1. **Full RAG Testing** (30 min)
   - Follow Test Suite 1 in MANUAL_TEST_PLAN.md
   - Use queries from TEST_QUERIES.md
   - Test semantic search accuracy

2. **Chat Features** (20 min)
   - Test Suite 2: Chat Basic Functionality
   - Multi-turn conversations
   - Markdown rendering

3. **UI/UX** (15 min)
   - Test Suite 3: UI/UX Features
   - Responsive design
   - Fullscreen mode

4. **Error Handling** (15 min)
   - Test Suite 5: Error Handling
   - Backend offline scenarios
   - Network issues

5. **Security** (10 min)
   - Test Suite 6: Security
   - XSS prevention
   - Prompt injection

---

## 📝 Quick Test Log

Track your quick tests:

```
Date: 2026-02-02
Time: 14:00
Tester: [Your Name]

✅ Environment verified
✅ All services started
✅ Widget opens
✅ First message sent
✅ RAG retrieval working
✅ Sources displayed

Issues Found:
- None

Ready for full testing: YES
```

---

## 🎯 Success Criteria

You're ready for full testing if:

- ✅ All services running without errors
- ✅ Widget opens and closes smoothly
- ✅ Can send and receive messages
- ✅ RAG retrieval shows in backend logs
- ✅ Sources are displayed in responses
- ✅ No console errors in browser
- ✅ Response times are acceptable (< 5 seconds)

---

## 📚 Next Steps

1. **Full Test Plan**: Open `MANUAL_TEST_PLAN.md`
2. **Test Queries**: Use `TEST_QUERIES.md` for pre-written queries
3. **Track Progress**: Use the test execution dashboard
4. **Report Issues**: Use the bug report template
5. **Document Results**: Fill out test execution logs

---

## 💡 Pro Tips

1. **Keep Logs Open**: Always watch backend logs during testing
2. **Use DevTools**: Network and Console tabs are your friends
3. **Test Systematically**: Follow the test plan order
4. **Document Everything**: Note even small issues
5. **Take Screenshots**: Visual evidence helps debugging
6. **Test Edge Cases**: Don't just test happy paths
7. **Compare with Docs**: Verify RAG responses against actual documentation
8. **Test Performance**: Note slow responses or timeouts

---

## 🆘 Need Help?

If you encounter issues:

1. Check backend logs: `backend/logs/dz_api_twin_backend.log`
2. Check browser console for JavaScript errors
3. Verify all services are running: `finch ps` and check ports
4. Re-run verification: `python backend/pre_test_check.py`
5. Restart services if needed

---

## ✅ Ready to Test!

You're all set! Open `MANUAL_TEST_PLAN.md` and start with **Test Suite 1: RAG Core Functionality**.

Good luck with testing! 🚀
