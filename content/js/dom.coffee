
class window.Controls.contentbox extends window.Control
    createDom: () ->
        w = @_int_to_px(@properties.width)
        h = @_int_to_px(@properties.height)
        """
            <div style="width: #{w}; height: #{h}; overflow: auto; word-wrap: break-word;">
                #{@properties.text}
            </div>
        """

class window.Controls.bigtextbox extends window.Controls.textbox
    createDom: () ->
        """
            <textarea class="control textbox #{@s(@properties.style)}" rows="#{@properties.lines}"
                    #{if @properties.readonly then 'readonly' else ''}>#{@properties.value}</textarea>
        """

class window.Controls.slider extends window.Control
    createDom: () ->
        width = @_int_to_px(@properties.width)
        """
            <div>
                <input type="range" style="width: #{width};" min="#{@properties.minvalue}" max="#{@properties.maxvalue}" />
            </div>
        """

    setupDom: (dom) ->
        super(dom)
        @input = $(dom).find('input')
        @input.val(@properties.value)
        @input[0].addEventListener 'change', (e) =>
            if @event 'change'
                @cancel(e)
        return this

    detectUpdates: () ->
        r = {}
        value = parseInt(@input.val(), 10)
        if value != @properties.value
            r.value = value
        return r
