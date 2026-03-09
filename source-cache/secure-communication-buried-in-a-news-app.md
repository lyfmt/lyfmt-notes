# Secure Communication, Buried In A News App

The article starts from a simple observation: cryptography is not always enough. Even if an adversary cannot read your messages, the very fact that you have a secure messaging app or are sending obviously encrypted traffic can be enough to put you at risk.

That is the problem The Guardian and researchers at the University of Cambridge tried to address with CoverDrop, a secure submission system built into a news app. The goal is not only to protect message contents, but also to make it harder to prove that private communication is happening at all.

## Hiding in plain sight

Many encrypted messaging apps share the same weakness: their presence can draw attention. If authorities or other adversaries can see that someone has a strongly encrypted messaging tool or is talking to a known secure server, that alone can create suspicion.

![CoverDrop architecture overview](https://hackaday.com/wp-content/uploads/2026/02/architecture-overview.png "The CoverDrop system architecture")

CoverDrop tries to solve this by integrating the mechanism into every copy of The Guardian’s app. Each installed app regularly sends small amounts of encrypted information to the system, even when there is no real message to deliver. Most of those transmissions are just meaningless cover traffic.

The article says that when a user does want to contact a journalist, the message and the source’s public key are encrypted with the journalist’s public key and then sent in a form that looks no different from ordinary cover traffic. Real and fake messages share the same size, the same timing, and the same encryption pattern, so network observers cannot easily tell them apart.

![Message submission inside the app](https://hackaday.com/wp-content/uploads/2026/02/screenshot_2.png "Messages in the app are encrypted and hidden")

At the receiving end, CoverDrop’s secure servers remove an initial layer of encryption so they can sort real messages away from the decoy traffic. The remaining encrypted messages are then delivered to journalists through a dead-drop style mechanism that pads real deliveries with some cover messages so that the drops always look the same size.

Because each real message also contains the source’s public key, journalists can reply through the same system using the reverse process. The result is secure two-way communication rather than a one-way anonymous tip box.

![Two-way communication in CoverDrop](https://hackaday.com/wp-content/uploads/2026/02/screenshot_4.png "CoverDrop supports secure two-way communication")

The article also highlights on-device security. The app stores message data in encrypted vaults that stay at a regular size and are modified on a fixed schedule whether covert communication is happening or not. Without the passphrase, there should be no obvious evidence that any secret messages exist.

Hackaday notes that the CoverDrop codebase is available on GitHub for people who want to audit or implement the design. It also argues that the project could appeal to many news organizations that need a deniable way for sources to submit sensitive information.

The final point is cautious rather than absolute: no system is perfectly secure, but a communication tool that focuses on deniability and traffic cover, not just message encryption, can materially reduce risk for sources and journalists.
