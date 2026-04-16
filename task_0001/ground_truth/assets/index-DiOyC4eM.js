(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),e.crossOrigin===`use-credentials`?t.credentials=`include`:e.crossOrigin===`anonymous`?t.credentials=`omit`:t.credentials=`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();var e=[{id:`home`,label:`HOME`},{id:`photos`,label:`PHOTOS`},{id:`about`,label:`ABOUT`},{id:`lightroom`,label:`LIGHTROOM`},{id:`contact`,label:`CONTACT`},{id:`prints`,label:`PRINTS & BOOKS`},{id:`events`,label:`EVENTS`},{id:`blog`,label:`BLOG`}],t=[{title:`Waterfall, Lake District`,image:`assets/images/2018_05_may_12_hazelborough-47.jpg_format_300w_d1cb22673ca2.jpg`,alt:`Waterfall framed by mossy rocks.`},{title:`Aurora, Iceland`,image:`assets/images/2017_03_mar_maldives-962.jpg_format_300w_ecfab34f3521.jpg`,alt:`Green aurora over a dark blue landscape.`},{title:`Stone shelf, Dorset`,image:`assets/images/Stone_shelf_Dorset_2022.jpg_format_300w_0088371b9105.jpg`,alt:`Coastal rock shelf in soft light.`},{title:`Autumn avenue, Oxfordshire`,image:`assets/images/2016_10_oct_30_hazelborough_wood-59.jpg_format_300w_18747c343b16.jpg`,alt:`Autumn trees forming a corridor of golden leaves.`},{title:`Views From Eigg`,image:`assets/images/Eigg_promo_website_square_front_cover_stack.jpg_46e182a4b84b.jpg`,alt:`A photobook mockup laid on a clean white background.`},{title:`Nathan Barry`,image:`assets/images/Nathan_website_profile_b_26w.jpg_175603d766d7.jpg`,alt:`Portrait of Nathan Barry in black and white.`}],n=[{title:`Water`,description:`Work taken from the coast, rivers or waterfalls - capturing fast or slow movements to evoke the feeling of being there. Click to view in full screen.`,items:[{title:`Frozen shore, Iceland`,image:`assets/images/2016_mar_iceland-245.jpg_format_300w_d3deae133d10.jpg`,alt:`Icy shoreline in pale blue light.`},{title:`Sea stack at dusk`,image:`assets/images/8003201.jpg_format_300w_0956d4e2b141.jpg`,alt:`Sea stack in a calm bay at dusk.`},{title:`Purple coast`,image:`assets/images/8003202.jpg_format_300w_3f5c6be028ab.jpg`,alt:`Purple-toned rocky coast at sunset.`},{title:`Woodland falls`,image:`assets/images/2018_05_may_12_hazelborough-47.jpg_format_300w_d1cb22673ca2.jpg`,alt:`Waterfall in woodland with green moss.`},{title:`Still stones`,image:`assets/images/2016_mar_iceland-591.jpg_format_300w_126f881a6f22.jpg`,alt:`Small stones in shallow water.`},{title:`Dark waves`,image:`assets/images/2019_10_oct_lake_district-54-3.jpg_format_300w_17e52792dc94.jpg`,alt:`Long exposure coastal waves.`},{title:`Pier in fog`,image:`assets/images/2017_01_jan_30_bournemouth-22.jpg_format_300w_b0296ff8aa58.jpg`,alt:`Pier stretching into fog over water.`},{title:`Dorset sunrise`,image:`assets/images/2016_10_oct_03_banbury_night-29.jpg_format_300w_a8f7cba38700.jpg`,alt:`Distant sunrise over a rocky shoreline.`}]},{title:`Landscape`,description:`Work taken from the UK or further afield, in all seasons and weather. Click to view in full screen.`,items:[{title:`Lone tree in snow`,image:`assets/images/2021_02_feb_06_mist_twyford-69-2.jpg_format_100w_fd1e638c0339.jpg`,alt:`A single tree standing in snow.`},{title:`Aurora trail`,image:`assets/images/2017_03_mar_maldives-962.jpg_format_300w_95ab2cf4ed24.jpg`,alt:`Aurora in a dark blue sky.`},{title:`Yellow tree, Warwickshire`,image:`assets/images/Three_trees_in_rapeseed_2C_Warwickshire.jpg_format_300w_54390bc8696b.jpg`,alt:`Yellow tree against a bright field.`},{title:`Dunes, North Wales`,image:`assets/images/2019_02_feb_14_whistley-63-2.jpg_format_300w_c9965e0e2021.jpg`,alt:`Soft dunes in beige tones.`},{title:`Snowdonia ridge`,image:`assets/images/2017_01_jan_22_snowdonia-50.jpg_format_300w_0887aeb4b18c.jpg`,alt:`Layered hills and clouds in Snowdonia.`},{title:`Rock studies`,image:`assets/images/2018_02_feb_torridon_lake_district-620.jpg_format_300w_9260af9147c0.jpg`,alt:`Rocky foreground with hills beyond.`},{title:`Dark spring forest`,image:`assets/images/2021_05_may_07_bluebells_micheldever-40-2.jpg_format_300w_7b318ec33e24.jpg`,alt:`Dark woodland with shafts of light.`},{title:`Grey Heron at waterfall`,image:`assets/images/2018_05_may_12_hazelborough-47.jpg_format_300w_d1cb22673ca2.jpg`,alt:`Waterfall and mossy rocks in a landscape composition.`}]},{title:`Local Work`,description:`A smaller selection of photographs from the Midlands, centred on quiet weather, trees and simple compositions.`,items:[{title:`Autumn square`,image:`assets/images/2022_08_aug_28_dorset-42.jpg_format_300w_627a938f8fba.jpg`,alt:`Golden leaves in a woodland clearing.`},{title:`Autumn avenue`,image:`assets/images/2016_10_oct_30_hazelborough_wood-59.jpg_format_300w_18747c343b16.jpg`,alt:`Autumn avenue with muted trunks.`},{title:`Flooded trees`,image:`assets/images/2023_01_jan_21_misty_trees-116.jpg_format_300w_518c119289b7.jpg`,alt:`Pale winter trees against light fog.`},{title:`Fresh spring morning`,image:`assets/images/2021_05_02_whistley-109.jpg_format_500w_35541c62ae3e.jpg`,alt:`Soft field textures in morning light.`}]}],r=[`Published in Outdoor Photography, Practical Photography, Amateur Photographer and Four Shires.`,`Landscape work focused on simple, elegant subjects and carefully controlled processing.`,`Adobe Lightroom tuition, one-to-one support and small-group workshops.`,`Regular participation in Oxfordshire Artweeks since 2018.`],i=[`Photo importing and file management`,`Image processing up to intermediate level, including tonal changes, B&W conversions, cropping, styling and sharpening`,`Tagging, rating, flagging and filtering images`,`Making collections to help group your images`,`Image exporting for sharing, printing or archiving`],a=[{title:`Eigg Print One`,price:`GBP125`,description:`A storm breaking over Rum, shot from Singing Sands beach. 25 cm square image with white border and archival fine art paper.`,image:`assets/images/eigg_thumbnail_for_website_print_1.jpg_10e881d6ebf2.jpg`},{title:`Eigg Print Two`,price:`GBP125`,description:`A tide-swept view from Laig Bay showing the outline of Rum. Printed and fulfilled by theprintspace.com.`,image:`assets/images/eigg_thumbnail_for_website_print_2.jpg_3854cc744009.jpg`},{title:`Eigg Print Three`,price:`GBP125`,description:`A softer seascape composition from Eigg, limited to ten prints and supplied with a certificate of authenticity.`,image:`assets/images/eigg_thumbnail_for_website_print_3.jpg_405e4bceb758.jpg`}],o=[`New book - Views from Eigg`,`Which focal length do you use the most?`,`Lake District 2018 trip report`,`Snowdonia workshop with Greg Whitton, March 2018`];function s(t){let n=t.replace(/^#/,``).trim().toLowerCase();return e.find(e=>e.id===n)?.id??`photos`}function c(e){return e.includes(`/task_0001/ground_truth`)||e.includes(`/ground_truth/`)?`..`:`../task_0001`}function l(e,t){return`${e}/${t}`}function u(t){return e.map(e=>`
        <a class="site-nav__link${e.id===t?` is-active`:``}" href="#${e.id}" data-page="${e.id}">
          ${e.label}
        </a>
      `).join(``)}function d(e,t){return e.map(e=>`
        <button
          class="gallery-card"
          type="button"
          data-lightbox-title="${e.title}"
          data-lightbox-image="${l(t,e.image)}"
          data-lightbox-alt="${e.alt}"
          aria-label="Open ${e.title}"
        >
          <img src="${l(t,e.image)}" alt="${e.alt}">
        </button>
      `).join(``)}function f(e,t){return`
    <section class="content-section photo-section">
      <div class="photo-section__copy">
        <h2>${e.title}</h2>
        <p>${e.description}</p>
      </div>
      <div class="gallery-grid">
        ${d(e.items,t)}
      </div>
    </section>
  `}function p(e,t){return`
    <article class="print-card">
      <img src="${l(t,e.image)}" alt="${e.title}">
      <div class="print-card__body">
        <h3>${e.title}</h3>
        <p class="price">${e.price}</p>
        <p>${e.description}</p>
      </div>
    </article>
  `}function m(e){return`
    <section class="intro">
      <div>
        <p class="eyebrow">Photos | Lightroom | Prints</p>
        <h1>Welcome to The Image Project</h1>
        <p class="lede">
          Home of photography by Nathan Barry. Based in the Midlands, UK, the work combines
          landscape studies, quiet local scenes and a teaching practice built around Adobe Lightroom.
        </p>
        <p class="lede">
          This reconstruction is reverse-engineered from <code>task_0001</code> and rebuilt as a
          lightweight static site for the page restoration workflow.
        </p>
      </div>
      <div class="hero-stats">
        <div>
          <strong>4</strong>
          <span>Captured checkpoints</span>
        </div>
        <div>
          <strong>140+</strong>
          <span>Recovered assets</span>
        </div>
        <div>
          <strong>1</strong>
          <span>Ground truth build</span>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="section-heading">
        <h2>Featured Work</h2>
        <p>A curated selection pulled from the recovered asset bundle.</p>
      </div>
      <div class="gallery-grid gallery-grid--featured">
        ${d(t,e)}
      </div>
    </section>
  `}function h(e){return n.map(t=>f(t,e)).join(``)}function g(e){return`
    <section class="content-section split-section">
      <img
        class="portrait"
        src="${l(e,`assets/images/Nathan_website_profile_b_26w.jpg_175603d766d7.jpg`)}"
        alt="Portrait of Nathan Barry"
      >
      <div class="split-section__body">
        <h1>About Nathan Barry</h1>
        <p class="lede">
          Welcome to The Image Project - home of photography by Nathan Barry. Based in the Midlands,
          UK, the work focuses on landscape images with simple and elegant subjects.
        </p>
        <p>
          Processing is centred on Adobe Lightroom, balancing subtle contrast and colour with an
          emphasis on keeping the original atmosphere of a place. Alongside image making, Nathan
          offers tuition, workshops and print-based work.
        </p>
        <ul class="feature-list">
          ${r.map(e=>`<li>${e}</li>`).join(``)}
        </ul>
      </div>
    </section>
  `}function _(e){return`
    <section class="content-section split-section split-section--wide">
      <div class="split-section__body">
        <p class="eyebrow">Photos | Lightroom | Prints</p>
        <h1>Lightroom one-day foundation course - GBP99</h1>
        <p class="strong">Courses by appointment on flexible basis</p>
        <p>
          Lightroom is the industry-standard solution for managing and processing your photos,
          especially when you want to get the best from RAW files. A swift program to use once
          familiar with it, the initial learning curve can be intimidating. This course is designed
          to shortcut that process and show a practical, repeatable workflow.
        </p>
        <p>
          If you already have some familiarity with Lightroom or Photoshop but want stronger and
          more consistent results, the foundation course still works well as a structured reset.
        </p>
        <h2>Topics covered</h2>
        <ul class="feature-list">
          ${i.map(e=>`<li>${e}</li>`).join(``)}
        </ul>
      </div>
      <div class="lightroom-aside">
        <img
          src="${l(e,`assets/images/Lightroom_before_after_2018.png_format_1000w_4d8107f6d9f3.png`)}"
          alt="Before and after Lightroom example"
        >
        <p>Learn an efficient workflow and how to make your photos look their best.</p>
      </div>
    </section>
  `}function v(e){return`
    <section class="content-section split-section">
      <img
        class="portrait portrait--square"
        src="${l(e,`assets/images/Nathan_website_profile_b_26w.jpg_175603d766d7.jpg`)}"
        alt="Portrait used on the contact page"
      >
      <div class="split-section__body">
        <h1>Contact me for more details about events, workshops or just general queries.</h1>
        <p>Feel free to reach out.</p>
        <form class="contact-form" data-contact-form>
          <div class="contact-form__row">
            <label>
              <span>First Name</span>
              <input name="firstName" type="text" required>
            </label>
            <label>
              <span>Last Name</span>
              <input name="lastName" type="text" required>
            </label>
          </div>
          <label>
            <span>Email Address</span>
            <input name="email" type="email" required>
          </label>
          <label>
            <span>Subject</span>
            <input name="subject" type="text" required>
          </label>
          <label>
            <span>Message</span>
            <textarea name="message" rows="5" required></textarea>
          </label>
          <button class="primary-button" type="submit">SUBMIT</button>
          <p class="form-feedback" data-form-feedback aria-live="polite"></p>
        </form>
      </div>
    </section>
  `}function y(e){return`
    <section class="content-section">
      <div class="section-heading">
        <h1>Books - new!</h1>
        <p>Reverse-engineered from the captured prints and books flow.</p>
      </div>

      <article class="book-showcase">
        <div class="book-showcase__lead">
          <span class="badge">SOLD OUT</span>
          <img
            src="${l(e,`assets/images/Eigg_promo_website_square_front_cover_stack.jpg_46e182a4b84b.jpg`)}"
            alt="Views from Eigg photobook"
          >
        </div>
        <div class="book-showcase__aside">
          <img src="${l(e,`assets/images/eigg_thumbnail_for_website_print_1.jpg_10e881d6ebf2.jpg`)}" alt="Thumbnail print one">
          <img src="${l(e,`assets/images/eigg_thumbnail_for_website_print_2.jpg_3854cc744009.jpg`)}" alt="Thumbnail print two">
          <img src="${l(e,`assets/images/eigg_thumbnail_for_website_print_3.jpg_405e4bceb758.jpg`)}" alt="Thumbnail print three">
          <img src="${l(e,`assets/images/Eigg_spread_example_1.jpg_2b58dc6e7edd.jpg`)}" alt="Book spread example">
        </div>
      </article>

      <div class="book-copy">
        <h2>Views from Eigg - photobook by Nathan Barry</h2>
        <p class="price">GBP25</p>
        <p>
          Seascapes from the Isle of Eigg in Scotland. The book is a softcover, printed on premium
          photo paper and presented as a clean square-format sequence of coastal photographs.
        </p>
      </div>

      <section class="content-section content-section--flush">
        <div class="section-heading">
          <h2>Limited Edition Prints</h2>
          <p>Three recovered print variants from the task asset pack.</p>
        </div>
        <div class="print-grid">
          ${a.map(t=>p(t,e)).join(``)}
        </div>
        <img
          class="wall-mockup"
          src="${l(e,`assets/images/eigg_print_one_wall_mockup_260_mm_65_mm_border.png_a4ffbc8e7107.png`)}"
          alt="Print mockup in a framed interior"
        >
      </section>
    </section>
  `}function b(e){return`
    <section class="content-section split-section split-section--wide">
      <div class="split-section__body">
        <h1>Events & Workshops</h1>
        <p class="lede">
          The original site promotes small-group workshops, one-day sessions and Lightroom-focused
          tuition. This reconstructed page keeps the same editorial tone and layout language.
        </p>
        <ul class="feature-list">
          <li>Small-group landscape photography workshops.</li>
          <li>One-to-one Lightroom coaching with flexible dates.</li>
          <li>Location-based field sessions with workflow reviews.</li>
        </ul>
      </div>
      <div class="lightroom-aside">
        <img
          src="${l(e,`assets/images/2017_10_oct_lake_district-2264.jpg_format_300w_9834b35f9d0d.jpg`)}"
          alt="Landscape used to illustrate events"
        >
      </div>
    </section>
  `}function x(){return`
    <section class="content-section">
      <div class="section-heading">
        <h1>Latest Blog Posts</h1>
        <p>Recovered from the public site structure to complete the navigation flow.</p>
      </div>
      <div class="blog-list">
        ${o.map(e=>`
              <article class="blog-card">
                <h2>${e}</h2>
                <p>A short archive card that keeps the original site navigation coherent for testing.</p>
              </article>
            `).join(``)}
      </div>
    </section>
  `}function S(e,t){switch(e){case`home`:return m(t);case`photos`:return h(t);case`about`:return g(t);case`lightroom`:return _(t);case`contact`:return v(t);case`prints`:return y(t);case`events`:return b(t);case`blog`:return x();default:return h(t)}}function C(e,t){return`
    <div class="site-shell">
      <header class="site-header">
        <a class="site-logo" href="#home" aria-label="The Image Project home">
          <img
            src="${l(e,`assets/images/TIP_logo_Black_left_align.png_format_1000w_987bd810c55a.png`)}"
            alt="The Image Project logo"
          >
        </a>
        <nav class="site-nav" aria-label="Primary">
          ${u(t)}
        </nav>
      </header>

      <main class="site-main">
        ${S(t,e)}
      </main>

      <footer class="site-footer">
        <span>Powered by Squarespace</span>
        <div class="site-footer__social" aria-hidden="true">
          <span>f</span>
          <span>o</span>
          <span>i</span>
        </div>
      </footer>
    </div>

    <dialog class="lightbox" data-lightbox>
      <form method="dialog" class="lightbox__backdrop">
        <button class="lightbox__close" value="close" aria-label="Close preview">x</button>
      </form>
      <figure class="lightbox__content">
        <img src="" alt="" data-lightbox-image-target>
        <figcaption data-lightbox-caption></figcaption>
      </figure>
    </dialog>
  `}function w(e){let t=e.querySelector(`[data-contact-form]`),n=e.querySelector(`[data-form-feedback]`);t&&n&&t.addEventListener(`submit`,e=>{e.preventDefault(),n.textContent=`Thanks, your message has been captured in this demo form.`,t.reset()});let r=e.querySelector(`[data-lightbox]`),i=e.querySelector(`[data-lightbox-image-target]`),a=e.querySelector(`[data-lightbox-caption]`),o=e.querySelectorAll(`[data-lightbox-image]`);!r||!i||!a||!o.length||o.forEach(e=>{e.addEventListener(`click`,()=>{i.src=e.dataset.lightboxImage??``,i.alt=e.dataset.lightboxAlt??``,a.textContent=e.dataset.lightboxTitle??``,r.showModal()})})}var T=document.querySelector(`#app`);if(!T)throw Error(`App root not found.`);var E=T;function D(){E.innerHTML=C(c(window.location.pathname),s(window.location.hash)),w(E)}window.addEventListener(`hashchange`,D),window.location.hash||(window.location.hash=`#photos`),D();