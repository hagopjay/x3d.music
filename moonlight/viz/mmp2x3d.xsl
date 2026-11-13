<?xml version="1.0" encoding="UTF-8"?>
<!--
  mmp2x3d.xsl : LMMS project XML  ->  X3D 4.0 scene (a 3-D piano roll)

  One XML vocabulary transformed into another, no code in between.
  Runs anywhere XSLT 1.0 runs: in the browser (XSLTProcessor), in Python (lxml),
  or with xsltproc on the command line:
      xsltproc mmp2x3d.xsl moonlight-two-ways.mmp > moonlight.x3d

  Mapping
    x  = time      (ticks / 48 = quarter notes, scaled by $sx)
    y  = pitch     (MIDI key, scaled by $sy, centred on middle C)
    z  = lane      (one lane per instrument track, in track order)
    box length = note length, box depth = velocity, colour = the track's colour
  Every note shares one DEF'd unit Box; every track shares one DEF'd Appearance,
  so 5,000 notes cost 5,000 Transforms but only 1 geometry and ~16 materials.
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" indent="no" encoding="UTF-8"/>

  <xsl:param name="tpq" select="48"/>
  <xsl:param name="sx" select="0.25"/>
  <xsl:param name="sy" select="0.14"/>
  <xsl:param name="lane" select="1.25"/>

  <xsl:variable name="hex" select="'0123456789abcdef'"/>
  <xsl:variable name="itracks" select="/lmms-project/song/trackcontainer/track[@type='0']"/>
  <xsl:variable name="nlanes" select="count($itracks)"/>
  <xsl:variable name="songlen">
    <xsl:for-each select="//midiclip">
      <xsl:sort select="@pos + @len" data-type="number" order="descending"/>
      <xsl:if test="position() = 1"><xsl:value-of select="(@pos + @len) div $tpq * $sx"/></xsl:if>
    </xsl:for-each>
  </xsl:variable>

  <!-- '#rrggbb' -> 'r g b' floats -->
  <xsl:template name="rgb">
    <xsl:param name="c"/>
    <xsl:param name="k" select="1"/>
    <xsl:variable name="h" select="translate(substring($c, 2), 'ABCDEF', 'abcdef')"/>
    <xsl:for-each select="(//node())[position() &lt;= 3]">
      <xsl:variable name="i" select="position()"/>
      <xsl:variable name="d1" select="string-length(substring-before($hex, substring($h, 2*$i - 1, 1)))"/>
      <xsl:variable name="d2" select="string-length(substring-before($hex, substring($h, 2*$i, 1)))"/>
      <xsl:value-of select="round(($d1 * 16 + $d2) div 255 * $k * 1000) div 1000"/>
      <xsl:if test="$i &lt; 3"><xsl:text> </xsl:text></xsl:if>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="/">
    <X3D profile="Interchange" version="4.0">
      <head>
        <meta name="title" content="LMMS project as an X3D piano roll"/>
        <meta name="generator" content="mmp2x3d.xsl"/>
      </head>
      <Scene>
        <WorldInfo title="{/lmms-project/song/trackcontainer/track[1]/@name}"/>
        <Background skyColor="0.02 0.02 0.05 0.06 0.05 0.12 0.10 0.07 0.16"
                    skyAngle="1.2 1.57" groundColor="0.02 0.02 0.05"/>
        <NavigationInfo type='"EXAMINE" "ANY"' headlight="true" speed="8"/>
        <DirectionalLight direction="-0.3 -1 -0.5" intensity="0.55" color="1 0.95 0.9"/>

        <!-- camera stations, one per section (taken from the first track's clips) -->
        <Viewpoint DEF="VP_OVERVIEW" description="Runway (overview)"
                   position="-10 12 14" orientation="-0.2036 -0.9705 -0.1295 1.1604" fieldOfView="0.9"/>
        <xsl:for-each select="$itracks[1]/midiclip">
          <xsl:variable name="cx" select="(@pos + @len div 2) div $tpq * $sx"/>
          <Viewpoint DEF="VP_{position()}" description="{@name}"
                     position="{$cx} 4 {6 + @len div $tpq * $sx * 0.42}"
                     orientation="1 0 0 -0.18" fieldOfView="0.9"/>
        </xsl:for-each>
        <!-- follow-cam: the page script slides this rig along x with the playhead.
             Moving a bound Viewpoint's parent Transform is the idiomatic X3D camera dolly. -->
        <Transform DEF="FOLLOW_RIG">
          <Viewpoint DEF="VP_FOLLOW" description="Follow the playhead"
                     position="-7 4.5 6" orientation="-0.5135 -0.8508 -0.1112 0.4986" fieldOfView="0.95"/>
        </Transform>

        <!-- shared unit geometry -->
        <Shape DEF="PROTO_HIDDEN"><Appearance><Material transparency="1"/></Appearance><Box DEF="UNIT" size="1 1 1"/></Shape>

        <!-- section floors -->
        <xsl:for-each select="$itracks[1]/midiclip">
          <Transform translation="{(@pos + @len div 2) div $tpq * $sx} -5.6 {-($nlanes - 1) * $lane div 2}"
                     scale="{@len div $tpq * $sx - 0.15} 0.04 {$nlanes * $lane + 1}">
            <Shape>
              <Appearance><Material diffuseColor="0.1 0.1 0.18" emissiveColor="{0.03 + (position() mod 2) * 0.03} 0.03 0.08" transparency="0.25"/></Appearance>
              <Box USE="UNIT"/>
            </Shape>
          </Transform>
        </xsl:for-each>

        <!-- note lanes -->
        <xsl:for-each select="$itracks">
          <xsl:variable name="i" select="position() - 1"/>
          <xsl:variable name="z" select="-$i * $lane"/>
          <xsl:variable name="col">
            <xsl:choose><xsl:when test="@color"><xsl:value-of select="@color"/></xsl:when><xsl:otherwise>#8899aa</xsl:otherwise></xsl:choose>
          </xsl:variable>
          <Group DEF="LANE_{$i}">
            <!-- lane rail -->
            <Transform translation="{$songlen div 2} -5.5 {$z}" scale="{$songlen} 0.02 0.04">
              <Shape><Appearance><Material emissiveColor="{0.25} 0.25 0.35"/></Appearance><Box USE="UNIT"/></Shape>
            </Transform>
            <xsl:for-each select="midiclip/note">
              <xsl:variable name="t0" select="../@pos + @pos"/>
              <xsl:variable name="vz" select="0.25 + @vol div 200 * 0.85"/>
              <Transform translation="{($t0 + @len div 2) div $tpq * $sx} {(@key - 60) * $sy} {$z}"
                         scale="{@len div $tpq * $sx * 0.92} {$sy * 0.85} {$vz}">
                <Shape>
                  <xsl:choose>
                    <xsl:when test="position() = 1">
                      <Appearance DEF="APP_{$i}">
                        <Material DEF="MAT_{$i}" shininess="0.6" specularColor="0.6 0.6 0.6">
                          <xsl:attribute name="diffuseColor"><xsl:call-template name="rgb"><xsl:with-param name="c" select="$col"/></xsl:call-template></xsl:attribute>
                          <xsl:attribute name="emissiveColor"><xsl:call-template name="rgb"><xsl:with-param name="c" select="$col"/><xsl:with-param name="k" select="0.25"/></xsl:call-template></xsl:attribute>
                        </Material>
                      </Appearance>
                    </xsl:when>
                    <xsl:otherwise><Appearance USE="APP_{$i}"/></xsl:otherwise>
                  </xsl:choose>
                  <Box USE="UNIT"/>
                </Shape>
              </Transform>
            </xsl:for-each>
          </Group>
        </xsl:for-each>

        <!-- playhead: a sheet of light the page script slides along x -->
        <Transform DEF="PLAYHEAD" translation="0 0 {-($nlanes - 1) * $lane div 2}">
          <Transform scale="0.05 12 {$nlanes * $lane + 1.5}">
            <Shape><Appearance><Material diffuseColor="1 1 1" emissiveColor="1 0.92 0.75" transparency="0.55"/></Appearance><Box USE="UNIT"/></Shape>
          </Transform>
          <PointLight DEF="PLAYLIGHT" color="1 0.85 0.6" intensity="0.9" radius="9" location="0 2 3"/>
        </Transform>
      </Scene>
    </X3D>
  </xsl:template>
</xsl:stylesheet>
