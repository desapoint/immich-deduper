
//------------------------------------------------------------------------
// LivePhoto Management
//------------------------------------------------------------------------
const key = 'livephoto'
const keyc = `.${key}`
const LivePhoto = window.LivePhoto = {
	hoveredVideo: null,
	modalVideo: null,
	visibilityObserver: null,

	init()
	{
		this.setupVideoErrorHandling()
		this.setupModalControls()
	},

	setupVideoErrorHandling()
	{
		const handleVdoList = (video) => {
			if (!video || video.tagName?.toLowerCase() !== 'video') return

			if (video.dataset.livephotoHandled) return
			video.dataset.livephotoHandled = 'true'
			this.observeGridVideo(video)
			video.addEventListener('error', () => {
				console.warn('[LivePhoto] load failed, hidden:', video.src)

				video.style.display = 'none'
				const span = video.closest('.viewer')?.querySelector(`span.livePhoto`)
				if(!span) {
					console.warn(`not found ${keyc} in viewer`)
					return
				}
				if(span) {
					span.innerText = `LivePhoto (can't play)`
					span.classList.add('red')
				}
				else {
					span.innerText = `LivePhoto`
					span.classList.remove('red')
				}
			})

			video.addEventListener('loadstart', () => {
				video.addEventListener('canplay', () => {
				}, { once: true })
			})
		}

		const handleModalVideo = (video) => {
			if (video.dataset.modalHandled) return
			video.dataset.modalHandled = 'true'

			const modal = video.closest('#img-modal')
			if (!modal) return

			const img = modal.querySelector('img')
			if (!img) return

			video.style.display = 'none'
			img.style.display = 'none'

			video.addEventListener('canplay', () => {
				video.style.display = 'block'
				img.style.display = 'none'
			}, { once: true })

			video.addEventListener('error', () => {
				video.style.display = 'none'
				img.style.display = 'block'
			}, { once: true })

			const updateProgress = () => this.updateModalProgress(video)
			video.addEventListener('loadedmetadata', updateProgress)
			video.addEventListener('durationchange', updateProgress)
			video.addEventListener('timeupdate', updateProgress)
			video.addEventListener('seeked', updateProgress)
		}

		document.querySelectorAll(`video${keyc}`).forEach(handleVdoList)
		document.querySelectorAll('#img-modal .livephoto video').forEach(handleModalVideo)

		const observer = new MutationObserver((mus) => {
			mus.forEach(mu => {
				mu.addedNodes.forEach(node => {
					if (node.nodeType == 1) {
						if (node.matches?.(`video${keyc}`)) handleVdoList(node)
						if (node.matches?.('#img-modal .livephoto video')) handleModalVideo(node)
						if (node.querySelectorAll) {
							node.querySelectorAll(`video${keyc}`).forEach(handleVdoList)
							node.querySelectorAll('#img-modal .livephoto video').forEach(handleModalVideo)
						}
					}
				})
			})
		})

		observer.observe(document.body, { childList: true, subtree: true })
	},

	observeGridVideo(video)
	{
		if (!('IntersectionObserver' in window)) {
			video.play()?.catch(() => {})
			return
		}

		if (!this.visibilityObserver) {
			this.visibilityObserver = new IntersectionObserver(entries => {
				entries.forEach(entry => {
					const target = entry.target
					if (entry.isIntersecting) target.play()?.catch(() => {})
					else target.pause()
				})
			}, {rootMargin: '160px 0px', threshold: 0.01})
		}

		this.visibilityObserver.observe(video)
	},

	setupModalControls()
	{
		document.addEventListener( 'click', ( e ) => {
			if ( e.target.id == 'livephoto-play-pause' )
			{
				this.toggleModalPlayback()
			}
			else if ( e.target.id == 'livephoto-progress-bar' || e.target.parentElement?.id == 'livephoto-progress-bar' )
			{
				this.seekModalVideo( e )
			}
		} )

	},

	toggleModalPlayback()
	{
		const video = document.querySelector( '#img-modal .livephoto video' )
		const button = document.getElementById( 'livephoto-play-pause' )

		if ( !video || !button ) return

		if ( video.paused )
		{
			video.play()
			button.textContent = 'Pause'
		}
		else
		{
			video.pause()
			button.textContent = 'Play'
		}
	},

	seekModalVideo( e )
	{
		const video = document.querySelector( '#img-modal .livephoto video' )
		const progressBar = document.getElementById( 'livephoto-progress-bar' )

		if ( !video || !progressBar ) return

		const rect = progressBar.getBoundingClientRect()
		const clickX = e.clientX - rect.left
		const percentage = clickX / rect.width
		const seekTime = percentage * video.duration

		video.currentTime = seekTime
	},

	updateModalProgress(video = document.querySelector('#img-modal .livephoto video'))
	{
		const modal = video?.closest?.('#img-modal')
		const progressFill = modal?.querySelector( '#livephoto-progress-fill' )
		const timeDisplay = modal?.querySelector( '#livephoto-time-display' )

		if ( !video || !progressFill || !timeDisplay ) return

		if ( video.duration > 0 )
		{
			const percentage = ( video.currentTime / video.duration ) * 100
			progressFill.style.width = percentage + '%'

			const currentMin = Math.floor( video.currentTime / 60 )
			const currentSec = Math.floor( video.currentTime % 60 )
			const totalMin = Math.floor( video.duration / 60 )
			const totalSec = Math.floor( video.duration % 60 )

			timeDisplay.textContent = `${ currentMin }:${ currentSec.toString().padStart( 2, '0' ) } / ${ totalMin }:${ totalSec.toString().padStart( 2, '0' ) }`
		}
	}
}

if ( document.readyState == 'loading' )
{
	document.addEventListener( 'DOMContentLoaded', () => LivePhoto.init() )
}
else
{
	LivePhoto.init()
}
