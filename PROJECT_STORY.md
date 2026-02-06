# The Project Story

## Why This Exists

This project isn't primarily about building something for others to use, though anyone is welcome to, and maybe it even takes off. The honest truth is that in a space moving this fast, it's hard to believe any particular tooling will have utility for very long. You can work to keep something current with its underlying platform (Claude Code, in this case), but eventually the utility it provides may simply be absorbed or rendered unnecessary. That said, my motivation is different from what drives most projects like this.

## The Problem: Complexity, Regression, and Lost Investment

The first motivation was deeply personal and practical. I have a complex, OSS project I have primarily developed with Claude Code, and the more evolved it becomes, the harder it is to keep everything aligned, working toward the vision, marching forward without regression. These are challenges with LLMs, sometimes severe ones, and the risk grows with every layer of maturity you add.

We've all been there: you put real work into building something, you come back for the next iteration, and it's broken, maybe by the slightest thing. And every once in a while, even the best model's answer is to *replace it*. Because one thing these models don't easily grasp is the investment that's already been made: the commitment, the maintenance, the maturity of what's there. To the model, it's a problem to solve. If it doesn't immediately understand the root cause, it may decide there's an easier alternative: swap in an off-the-shelf library, or rebuild from scratch. That's not an uncommon outcome.

Then there are the iteration loops. When you're working with larger, more complex codebases, or having to digest large pieces of documentation while conducting work, it's remarkably easy to try four approaches, fail, and circle back to the first one you already tried. I have no doubt the Claude Code team is constantly and cautiously working to address this kind of problem. We all know that memory is one of the biggest challenges that will be tackled in the next year across agentic coding and agentic work in general. But it's still a real problem today.

I fully respect that the labs are cautious about how they advance more complex tooling; it can backfire more often than it solves individual problems. But these issues are critical to me in the context of the project I'm working on. I've hit them, fought them, and had parts of my project regress because of them. So I decided to build something.

## The Origin: A Research Agent That Actually Worked

It started simply, based on experience from another project, porting Pocket TTS to iOS using Rust and Candle. There, I had just two or three extra agents, nothing more than prompts that I would run independently. The real value was independent utility.

I had a research agent that I would use to get the effort back on track. We were in one of those situations where we needed a very high level of success, but getting those last percentage points is always the hardest part, and we were literally stuck, unable to progress forward at all. By having an independent research agent take a fresh look at everything, including full-blown fresh research on the web, that day, that moment, based on where we had progressed so far, was transformative. We wuld often find out what really was the next thing to try and it was the key to our sucess in that project. 

It worked. It worked quite well. And that gave me the idea for what I'm building here.

## The Exercise: Building a Best-of-Breed Multi-Agent System

The other motivation was the exercise itself. I'd been itching to create a proper multi-agent setup for some time. I use patterns like this already, not by downloading other products, but through my own approaches using Claude Code's features and functionality. But I wanted to go through the discipline of building a best-of-breed system for my specific use case, focused on what actually matters to me.

## What Matters: Three Levels of Protection

What matters to me comes down to three levels.

**First: Vision.** For a lot of people, this kind of concern is not primary; they're focused on giving unbridled capabilities to a multi-agentic system, and I completely understand and respect that. It probably works best in many cases. But for me, especially in my current project, and in many of the ideas and visions I come up with, the *vision itself* is what matters most. It's essential that every piece of work being done serves that vision.

**Second: Architecture.** You put real effort into architecture. And while it's increasingly common for people to focus on architecture that is entirely evolved and created by agents as the best way to accomplish the desired outcome (that's powerful, and I think it will become much more standard in the future), with a project like the one I'm working on now, many of these architectural decisions are really critical.

One example: my open source voice learning system has a primary voice pipeline. How speech is turned into text, whether or not it's transmitted to an LLM (if that's even part of the mix), and then how text is converted back to speech. There are certain settings, certain capabilities, certain methodology involved, and the idea is that this pipeline should be used by all such activities in the app. But more than once, while working on a piece of functionality, even though I tried to verbalize that and make sure it got into the CLAUDE.md, a brand new pipeline was created instead. Brand new code for doing things like text-to-speech, from scratch, rather than using the established architecture.

This is part of what led me to this tool: the idea that when we formalize architectural decisions, those decisions are *enforced*. That every time we're doing work, the architecture is used as guidance in driving the acceptance of decisions and the work to be done.

**Third: Rules.** These could be simple things: test coverage thresholds, build-and-test patterns, what to do every time you finish a block of work like running a set of tests. Whatever the rules are, I want them part of the mix too. And we know this is always a difficult part, because LLMs can't really follow rules. They do fairly well when everything is fresh: fresh context, a very reasonable amount of bootstrap information. For instance, what comes in CLAUDE.md that is clear, not overwhelming, non-contradictory, and well-worded, it'll appear like it's perfectly following the rules at the start. But that won't last. The details of when and how things fall apart aren't important. It's just that by the very nature of how LLMs work, that's what we have.

Anything that is able to more assuredly or deterministically guarantee the following of such rules is not the LLM itself; it's tooling. You could certainly make it *seem* like an LLM perfectly follows rules and never misbehaves if you have enough filters and firewalls in front of it to ensure none of that breaks through. So it's artificial, it's a perceptive issue. And that's certainly a lot of what I have here, in a sense. But again, I wanted agency and capability too.

## Intercepting Ideas Early

So part of what I thought about is: if it's possible to intercept ideas early, so that a whole huge session spent building something, only to have it evaluated at the end and find out it's not serving the vision or it's breaking a rule and gets thrown out, that doesn't seem very efficient. I decided it was really important to see what could be done to intercept ideas and decisions *before* the work is actually done.

I wasn't really sure what could realistically be done here, but it turns out that Claude Code, which I was building this on as the foundation of the tool, has capabilities built in that facilitate this. And timing became king too, because these capabilities are fairly new. They're a natural evolution of existing capabilities (the to-do list), but this new Task system that's been out for just a few weeks has a lot more capability and provides exactly what I needed: intercept these things early, block them until they've been reviewed, and then release them to be worked on by worker agents to actually get the job done, once it's been determined that the planned activity is safe and passes review.

## Open Source, Open Story

This whole project is open source and I will continue to work on it. My promoting of it will really just be about telling the story of why I did it and sharing one vision of agentic tooling, purely from an academic standpoint. If it crosses the line eventually into something that's a product, if I decide I want to put more effort into polishing it for the general public, then we'll see if we get there and what happens at that point. But for now, it's really just one more piece of tooling for my own use, and another mental exercise to just exercise the muscles and engage the problem space of agentic coding and agentic tooling.
