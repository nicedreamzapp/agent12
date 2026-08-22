Write a single self-contained HTML file that renders an interactive furry ball with WebGL2.

Requirements:

1. One file. No libraries, no CDN links, no imports, no external assets. Inline all CSS and JS.
2. A sphere covered in hair. Every strand is a separate piece of geometry, not a texture. Render at least 200,000 strands; 1,000,000 is the target. Distribute the roots evenly over the sphere (a Fibonacci/golden-angle lattice works).
3. Scale: the ball is 8 inches across and each hair is about 1 inch long.
4. The strands must be lit so they read as hair rather than a glowing shell: shade along the strand, darken the roots, and let the coat occlude itself. Vary strand length and brightness a little so the silhouette is fuzzy.
5. Dragging the mouse across the ball must bend the strands under the cursor in the direction of the drag, as if a hand were petting the fur. The bend must persist behind the stroke and relax back over roughly half a second. Dragging must NOT rotate the camera.
6. The canvas fills the window, the background is dark, and the animation runs on requestAnimationFrame.
7. It must run at an interactive frame rate on an Apple Silicon GPU. Draw the strands in as few draw calls as you can.

Output ONLY the contents of the HTML file. No explanation, no markdown fences.
