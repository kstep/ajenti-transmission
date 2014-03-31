
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
