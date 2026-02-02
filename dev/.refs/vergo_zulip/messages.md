# Zulip Messages

Scraped: 2026-02-02T11:09:00.596527
Total: 9 messages

---

## Machine Learning for Theorem Proving > unknown

### Eric Vergo (2026-02-02 11:08)

> Kim Morrison said:
> 
> I think Eric Vergo's example above is interesting to look at. There's no doubt that the AIs are already capable of creating repositories with correct (perhaps not interesting) mathematics, checked by Lean.
> 
> 
> For what it's worth, I think the math here is interesting. I say this not to put up a stink, but because I think it's relevant to the discussion we are having: Who gets to decide what it means for some piece of mathematics to be interesting?
> Timothy Chow said:
> 
> If we go down the route of publishing a list of recommendations, then we should be mindful that mathematicians hate being told what to do. I'm reminded of the brouhaha that Jaffe and Quinn's article on Theoretical Mathematics generated. Atiyah responded by saying that even though he agreed with much of what they said,  "I rebel against their general tone and attitude which appears too authoritarian." In order to minimize backlash, we will need to avoid sounding too authoritarian.
> 
> 
> This is front and center for me. I know that I am a bit of an outsider here, so I would like to take a minor detour and tell you a bit about my background. I do this not to draw attention to it, but to share it with the hope that you fully understand where I am coming from, add some credence to my thoughts, and to give you confidence that I mean what I say. I know who all of you are and given the nature of the conversation I think it makes sense that you know who I am.
> In August of 2024 I was interviewed on a podcast, where I describe the process of leaving my mechanical engineering career at Apple to pursue mathematics. It is surprising how many things I say during that interview that are relevant to the conversation we are having right now, but the important part is said at the 13:00. (timestamped link at the end of this post, it lasts  5 mins). Additionally, in October of 2023 I wrote “Math is now an Engineering Problem” on my now defunct blog. The critical part of that post is this: 
> “Just as Napster was the first warning shot to the music industry that everything was about to change, Sagredo is the first warning shot to mathematicians. 
> While an incredible achievement, there are numerous opportunities to make this technology significantly more effective; specifically trained LLMs will do a better job of generating error free code, optimization will make the ‘discussion’ between the two subsystems faster, more compute will lead to speed ups. The list goes on. But that list is supplanted in importance by the following observation: everything on that list is a matter of engineering – not mathematics. And, in just the same way the LLM uses the iterative process to ‘engineer’ a proof, we will be able to apply the iterative process to engineer the system itself. What this means is that the ability of this system to produce proofs is a function of our ability to engineer the system, rather than our ability to understand mathematics – it’s engineering all the way down.”
> Is it fair to say that the repo I shared earlier in this thread was made with Sagredo++? I think it is. 
> The core responsibility I had as an engineer was to take product designs/architectures which had been validated at low volume and get the product design refined to the point where it can be put into customers hands. This involved designing things that could be manufactured, sometimes in the many millions of units, while maintaining high quality standards. If my time as an engineer taught me anything, it’s that more is different. Different in a way that is not “we keep finding new corner cases that break the kernel” or “This process is the latest bottleneck in build time, that’s a first”. I mean different in a way that no one can predict, different in a way that simply cannot happen unless you are doing things at scale and have a large number of things interacting. When I looked at the coupling of large language models and formal verification systems, I saw something that could be automated and scaled, which led to that blog post. Based off of what I have seen between then and now, I fully expect the tools to become increasingly powerful. What happens as a result of that is very hard to predict.
> Like a lot of people here, I am drawn to and excited by the exacting and brutal standards that formal verification imposes. What excites me more is the fact that I will get to express my creativity while being grounded by Lean. LLMs will be a part of my workflow moving forward and it’s clear that this is true for others as well. I look forward to developing best practices around this that fully respect the rigor that Lean demands, and to do so in a way that increases accessibility while adhering to open source philosophies. I do not know “how to do this right”, and I don’t think anyone does. But we will figure something out.
> https://www.youtube.com/watch?v=-3TZG1NiFKA&t=780s

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/558062623)

---

### Eric Vergo (2026-02-02 11:08)

> Tremendous. Thank you for both requesting the clarifications and working through my explanations. Shared understanding is important and I did a poor job of making that possible. I’d like to build on that and tie up a few loose threads.
> Timothy Chow said:
> 
> Eric Vergo said:
> 
> Are there good arguments against full transparency beyond the overhead added when producing proofs?
> 
> 
> What exactly do you mean by "full transparency"? 
> 
> 
> By full transparency I mean two different things. First, and much less of a concern on my end, are end user mathematicians disclosing the use of “AI” tools, along with the logs and techniques used in doing so. Indeed, it is not the norm now that mathematicians publish failed attempts and time spent on wrong ideas. But I would argue that this is, in part, a function of the fact that doing so has been unavailable to mathematicians because of pragmatic constraints. But, the introduction of these tools significantly reduces the amount of work needed to execute on that, so maybe we should consider it. As others in the thread have noted, people may engage in undesired behavior when disclosing use in AI, and this needs to be taken into account. I don’t have solutions for much of, if anything highlighted here but do mirror the concerns that others have shared.
> The far greater concern, and the intent of my previous posts, is to push for full transparency from companies who are producing the tools that we are going to use. What I mean by that is this: right now we are relying on the good graces of frontier model makers to have access to things like reasoning traces, a full history of actions taken, outputs, intermediate artifacts, tool calls, logs, etc. There is no guarantee that they will do this in the future, and there are already examples of end users having unexpectedly reduced access to these types of things. I am deliberately not including examples to avoid finger pointing, but a quick search will confirm this. I’m bringing this up to illustrate a point: there are implicit assumptions being made that we will always have the option of inspecting every token involved in producing a proof, and the reality is that the option may not always be there.  I am not making the claim that we should make it the norm that mathematicians share all of their relevant LLM interactions moving forward, but I could imagine a future where it is. Moreover, if the norm settles at a ‘less invasive’ level some may want to still choose to share as much as possible. If that is something we want to enable, we should make that clear now. 
> These companies are anticipating that this technology will allow them to capture trillions of dollars in value over the coming years. We should expect them to act in a way that is rational when evaluated against the incentive structures surrounding them. This is not ascribing malice to their actions, simply observing that they are operating in a competitive, high stakes environment. If we want something that is in tension with what they want, we may have to fight hard for it. 
> Timothy Chow said:
> 
> Thanks for the clarification. Let me clarify what I intended by my "amusing possibility." I had in mind LLM-generated proofs written entirely in natural language that sound highly plausible to a professional mathematician, but which are incorrect in the mathematician's sense: i.e., the proof contains huge gaps or even outright false statements. Emily gave an example (maybe not highly plausible, but at least somewhat plausible to a non-expert) early on in her talk.
> 
> 
> You are very welcome. I thought Lean was going to be able to easily insulate itself from the type of things Emily shared, but it might not. 
> Timothy Chow said:
> 
> Your repo also serves as an important cautionary tale, but of a slightly different kind from what I had in mind.
> 
> 
> A cautionary tale indeed. Even though they are providing legitimate value, LLM based tools and their outputs need to be treated in an adversarial way. 
> Timothy Chow said:
> 
> Yet another kind of cautionary example would be of seemingly formally verified results that are wrong in a strong sense. If you search for "maliciously doctored" in Mark Adams's slides on "Flyspecking Flyspeck" then you'll see an example of what I mean. One can also imagining maliciously doctoring GMP or some other infrequently scrutinized section of the trusted code base to create a false proof that builds without errors.
> 
> 
> This may not even require the malice of a human pilot, just more reward hacking and someone who is not paying attention or is unaware of what is going on.

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/558327426)

---

### Eric Vergo (2026-02-02 11:08)

> Kim Morrison said:
> 
> Eric Vergo said:
> 
> Just as Napster was the first warning shot to the music industry that everything was about to change, Sagredo is the first warning shot to mathematicians.
> 
> Thanks for the Sagredo shout-out. :-) I'm glad someone noticed it!
> 
> I showed it to so many people and no one 'got it'. I couldn't believe what I was seeing, or peoples lack of reaction. I'm sure you are busy with the modules launch (which looks awesome!), but I do think we should develop the tool you mentioned if/when you get some time. I'd be happy to use this repo and others for some stress testing :)

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/558465939)

---

### Eric Vergo (2026-02-02 11:08)

> Johannes Schmitt said:
> 
> Eric Vergo This sounds very interesting (will read up on your precise proposal), but please do go ahead with using this as a case study! Very happy to provide any assistance you might need.
> 
> Great, this will take me a day or two and I'll post here when things are ready.

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/563840651)

---

## general > unknown

### Eric Vergo (2026-02-02 11:08)

> Jason Rute said:
> 
> Eric Vergo, I have a lot of reservations about your system.
> 
> All of the points here are well taken. In the interest of keeping this thread focused I will start a new thread for this tool. (maybe a mod should break it off?)

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/565681013)

---

### Eric Vergo (2026-02-02 11:08)

> David Thrane Christiansen said:
> 
> Eric Vergo said:
> 
> more tightly couple the css classes generated by Subverso to actual lean
> 
> Can you say more about what you mean here?
> 
> Sure, there are a few specific points behind this. For instance, right now SubVerso is tagging a lot of lean text as unknown, including things that would have different styling if it were rendered in, say, live.lean-lang. 
> For example, In the 'computing types code' many of the punctuation characters, such as "( ) : = >" get tagged as 'unknown', meaning they all have the same styling applied via css. If we want to replicate this we would need more granularity on the classes. 
> Screenshot 2026-01-08 at 1.20.45 PM.png
> Screenshot 2026-01-08 at 1.21.07 PM.png

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/567007897)

---

## lean4 > unknown

### Eric Vergo (2026-02-02 11:08)

> Jon Eugster said:
> 
> Eric Vergo said:
> 
> When showing Lean to my professors and other students I have been met with responses such as “gross” and “this looks awful”.
> 
> For what it's worth, I'm still quite amazed about how beautiful Lean as a Language is, while being as expressive as it is! In my opinion it's way better than latex source code! But you are certainly right about certain ideas how to display things.
> 
> I’m still amazed at the fact anything like this could exist at all. That's why I keep trying to share it with people!

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/473141441)

---

## maths > unknown

### Eric Vergo (2026-02-02 11:08)

> Joseph Myers said:
> 
> Eric Vergo said:
> 
> 
> Do you have particular material you're looking to formalize for which you want additive tilings? For example, are you planning to formalize some of the Greenfeld-Tao papers?
> 
> 
> Actually I was hoping you could tell me.
> 
> 
> Tiling is a large field with a lot of activity in recent years, so it helps if you have an idea of things you're aiming to formalize. You could take almost any result from Tilings and Patterns, or from any paper in the subject since that book was written in the 1970s, for example. Some things might focus heavily on the combinatorial side (say if you wanted to formalize Berger's theorem that whether a set of Wang tiles admits a tiling is undecidable, possibly using one of the later presentations of the proof such as Robinson's). Some things might depend heavily on the geometrical and topological side (say if you wanted to formalize a proof that all topological discs that tile the plane using translated copies only can also do so with the tiles arranged in a lattice; Kenyon and others). Some things might heavily involve the computational side.
> 
> 
> There are many things in this space I'm looking to formalize. Beyond verification, my intent in formalizing is to strengthen my understanding. I 'learn by doing' and the hope is that formalizing tiling theory will help me understand both the established results I half-understand and things I have found like the one above. That being said, it really looks like we may not have a ‘one size fits all’ definition. 
> One 'intermediate' result I was considering going after was the classification of frieze/wallpaper groups. After reading and thinking about it more, I'm now realizing the following: we theoretically could come up with some definition of tiling and use it in those classification theorems, but it isn't required. I bring this up because we are discussing 'how should we define tiling' and it has caused me to realize that something I thought was about tilings isn't. Is it fair to say that these theorems "are really about the underlying symmetry groups of the space, and tiles are just a convenient way to think about them"?

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/566811416)

---

## new members > unknown

### Eric Vergo (2026-02-02 11:08)

> Hey all,
> I’m a mechanical engineer by trade and spent the last decade on the product design team at Apple. I spent my time there designing Macs, but recently left and will be pursuing a masters in math at Queens college starting this fall. I’m excited to dive in, and learn all of the things I missed the first time around. I’m still very much at the beginning of my higher-level math journey, but it is clear to me that ITPs are the future of mathematics. 
> Let’s build something great.

[View on Zulip](https://leanprover.zulipchat.com/#narrow/id/365896813)

---
