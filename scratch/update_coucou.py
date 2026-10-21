with open(r'frontend/src/components/CoucouIsland.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. State definition
s_target = 'const [copied, setCopied] = useState(false);'
s_replacement = '''const [copied, setCopied] = useState(false);
  const [emailTaskAdded, setEmailTaskAdded] = useState(false);'''

assert s_target in content, 's_target not found'
content = content.replace(s_target, s_replacement, 1)

# 2. Outlook card body update
card_target = '''                      <div className="text-[13px] font-bold text-white line-clamp-1 mb-1">
                        {outlookAlert.subject}
                      </div>
                      {outlookAlert.summary && (
                        <div className="text-[11.5px] text-neutral-300 line-clamp-2 leading-relaxed">
                          {outlookAlert.summary}
                        </div>
                      )}'''

card_replacement = '''                      <div className="text-[13px] font-bold text-white line-clamp-1 mb-1">
                        {outlookAlert.subject}
                      </div>
                      {outlookAlert.is_task && outlookAlert.task_title ? (
                        <div className="flex flex-col gap-0.5 p-2 rounded-lg bg-emerald-950/40 border border-emerald-500/30 my-1 animate-in fade-in duration-150">
                          <div className="flex items-center justify-between text-[11px] font-bold text-emerald-200">
                            <span className="truncate">⚡ {outlookAlert.task_title}</span>
                            <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 flex-shrink-0 ml-1">
                              {outlookAlert.task_priority || 'High'}
                            </span>
                          </div>
                          {outlookAlert.task_description && (
                            <p className="text-[10px] text-neutral-300 line-clamp-2 leading-tight">
                              {outlookAlert.task_description}
                            </p>
                          )}
                        </div>
                      ) : outlookAlert.summary ? (
                        <div className="text-[11.5px] text-neutral-300 line-clamp-2 leading-relaxed">
                          {outlookAlert.summary}
                        </div>
                      ) : null}'''

assert card_target in content, 'card_target not found'
content = content.replace(card_target, card_replacement, 1)

# 3. Actions row button
btn_target = '''                    ) : outlookAlert ? (
                      <div className="flex items-center gap-1.5">
                        {outlookAlert.suggested_reply && ('''

btn_replacement = '''                    ) : outlookAlert ? (
                      <div className="flex items-center gap-1.5">
                        {outlookAlert.is_task && outlookAlert.task_title && (
                          <button
                            onClick={async () => {
                              sounds.playClick();
                              try {
                                await api.createTask({
                                  title: outlookAlert.task_title!,
                                  description: outlookAlert.task_description || outlookAlert.summary || outlookAlert.subject,
                                  source: `outlook_${outlookAlert.sender || 'email'}`
                                });
                                setEmailTaskAdded(true);
                                sounds.playComplete();
                                voice.speak("Task added to your list.");
                                onTasksRefresh();
                                setTimeout(() => setEmailTaskAdded(false), 3000);
                              } catch (e) {
                                console.error(e);
                              }
                            }}
                            title="Add actionable task or ticket to your pending tasks"
                            className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold transition active:scale-95 cursor-pointer shadow-xs"
                          >
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                            <span>{emailTaskAdded ? 'Added!' : 'Add to Tasks'}</span>
                          </button>
                        )}
                        {outlookAlert.suggested_reply && ('''

assert btn_target in content, 'btn_target not found'
content = content.replace(btn_target, btn_replacement, 1)

with open(r'frontend/src/components/CoucouIsland.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('CoucouIsland.tsx updated successfully!')
