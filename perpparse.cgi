#!/usr/bin/perl -T
######################################################################
# PerpParse - Small script to read in perplog generated log
#             files and parse them into a pretty, usable format.

use CGI qw(:standard);
use Date::Manip;
use strict;
use warnings;
use YAML;

# Default variables
my $ver = '4.0';
my $configfile = '../config.yaml';
my $config = YAML::LoadFile($configfile);

# Proceed with normal log display, and make sure we've been passed a log file.
my $l;
my $line = 0;
if (param('l')) {
    $l = param('l');
    # Check to make sure it's not malformed, if it is, use today's date.
    if (! ($l =~ /^\d\d\d\d\d\d\d\d$/)) {
	$l = todaysdate();
    }
} 
# If we don't get a logfile, snag the current date.
if (!$l) {    
    $l = todaysdate();
}
# Use the date to load a perplog irc log.
my $log = $config->{logroot} . "irclog." . $l . ".wiki";

# Print Header
print "Content-type: text/html\n\n";

#=========================================================================
# Place for dealing with custom crap. 
if ($config->{ffoption} && (param('y') && param('m') && param('q'))) {
    PrintQuoteAdd(param('q'), param('y'), param('m'));
    exit;
}
#=========================================================================

# Print out Header info and global navigation.

PrintHead($l);
PrintNav($l);

# Check if we got passed an 'r' param, standing for reverse, and if we did 
# we're going to print the quote box here instead of at the bottom.
if (param('r') && $config->{ffoption}) {
    PrintQB($l);
}

print "<p class=\"log\">";

# Open the log, and read it into a variable and then close it. 
open(LOG, "<$log") || print "The log for this day \"irclog.$l.wiki\" does not exist.\n";
my @rows = <LOG>;
close(LOG);

# Reverse Rows if needed
if (param('r')) { 
    @rows = reverse(@rows);
}

# Start parsing the log file.
my $q = '';
foreach (@rows) {
    #Parse the lines in the log file, but only parse the timestamped lines. 
    if ($_ =~ /\[200/) {

	# Prep for adding to quote file, $q tracks the plaintext version of 
	# the quote, while $_ continues to hold the value that will get rendered 
	# in html.
	$q = $_;
	$q =~ s/\"/\'/g;

	# Remove all <>'s to Catch HTML tags that can do bad things
	$_ =~ s/</\&lt\;/g;
	$_ =~ s/>/\&gt\;/g;

	# Drop the date stamp and seconds
	$_ =~ s/^\[200\d-\d+-\d+\s(\d+:\d+):\d+\]\s/\[<span class=\"date\">$1<\/span>\] /;
	$q =~ s/^\[200\d-\d+-\d+\s(\d+:\d+):\d+\]\s//;

	# Drop wiki bracketing
	$_ =~ s/\[\[//;
	$_ =~ s/\]\]//;
	$q =~ s/\[\[//;
	$q =~ s/\]\]//;

	# Drop nids and replace with breaks
	$_ =~ s/\{nid\s.+\}/<br\/>/;
	$q =~ s/\{nid\s.+\}//;

	# Color Nicks
	$_ =~ s/\&lt\;([a-zA-Z0-9]+)\&gt\;/<span class=\"brac\">&lt\;<\/span><span class=\"nick\">$1<\/span><span class=\"brac\">&gt\;<\/span>/;

	# Parse URLs
	if ($_ =~ /(http:\S+)/ ||
	    $_ =~ /(https:\S+)/) {

	    # Catch common image formats, and display them resized with 
	    # a link to the original.
	    if ($_ =~ /png|jpg|bmp|gif/ ) {
		$_ =~ s/(http:\S+)/<a href=\"$1\"><img src=\"$1\" width=\"30%\" border=\"0\"><\/a>/;
	    } else {

		# Process Links
		my $urltext = $1;
		if (length($urltext) > $config->{maxurlsize}) {

		    # If URL is too long, truncate it. This removes those 
		    # nasty 400 character links for the logs.
		    my $ln = length($urltext);
		    $urltext = substr($urltext,0,($config->{maxurlsize} / 2)) . 
			'...' . substr($urltext,($ln - ($config->{maxurlsize} / 2)));
		}
		$_ =~ s/ (http:\S+)/ <a href=\"$1\">$urltext<\/a>/;
		$_ =~ s/ (https:\S+)/ <a href=\"$1\">$urltext<\/a>/;
	    }
	}
	chomp $q;


	# Nick catching.
	if ($config->{nickmethod}) {
	    my $nicks = YAML::LoadFile($config->{nickfile});
	    my $username;
	    if ($config->{nickmethod} eq 'auth') {
		$username = $ENV{REMOTE_USER};
	    } elsif ($config->{nickmethod} eq 'drop') {
	        $username = param('nick');
	    }
	    if ($username) {
		foreach my $nick (@{$nicks->{$username}}) {
		    if ($_ =~ /$nick/ && !($_ =~ />$nick</) && 
			!($_ =~ /\*\s$nick/) &&
			!($_ =~ /has joined/) &&
			!($_ =~ /is now known as/)) {
			$_ =~ s/\b($nick)\b/<span class=\"hl\">$1<\/span>/gi;
			$_ =~ s/\b($nick):\b/<span class=\"hl\">$1<\/span>:/gi;
		    }
		}
	    } 
	}
	
	# Set the line up for dragging. 
	print "<span id=\"$q\">$_</span>";
	if ($config->{ffoption}) {
	    print "<script type=\"text/javascript\">
               new Draggable(\"$q\", {revert:true})</script>";
	} 
	
	$line++;
    }    
}
print "</p>";

# Reprint the global navigation.
PrintNav($l);

# If we didn't get a reverse param, print the quotebox.
if (!param('r') && $config->{ffoption}) {
    PrintQB($l);
};
PrintFoot();
    
sub PrintNav {
    my $date = shift;

    # Find the correct previous and next logs.
    my ($blink, $flink);
    if ($date) {
        $blink = substr(DateCalc($date . "12:00:00","- 1day","Date Error"), 0, 8);
	$flink = substr(DateCalc($date . "12:00:00","+ 1day","Date Error"), 0, 8);
    } else {
	$blink = substr(DateCalc("today","- 1day","Date Error"), 0, 8);
	$flink = substr(DateCalc("today","+ 1day","Date Error"), 0, 8);
    }
    print "<table><tr><td valign=\"middle\">";
   
    # Param building, grab the params we care about and pass them.
    my ($params, $rparams) = getParams();

    ## Start Printing
    # Reverse Button
    print "<a href=\"$config->{scriptname}$rparams";
    if ($l ne todaysdate()) {
        print "&l=$l";
    }
    print "\"><img src=\"$config->{imgdir}sort.jpg\" border=\"0\"";
    if ($params =~ /r=t/) {
        print "alt=\"Reverse Order\" title=\"Reverse Order\"></a> ";
    } else {
        print "alt=\"Chronological Order\" title=\"Chronological Order\"></a> ";
    }

    # Back Link
    print "</td><td valign=\"middle\">\&nbsp;
           <a href=\"$config->{scriptname}$params" . "&l=$blink\">Back a Day</a> | ";

    # 'Today' Link
    if ($date eq todaysdate()) {
        print "Today's Log";
    } else {
        print "<a href=\"$config->{scriptname}$params\">Today's Log</a>";
    }

    # Forward Link
    if ($date eq todaysdate()) {
        print " | Forward a Day";
    } else {
        print " | <a href=\"$config->{scriptname}$params" . "&l=$flink\">
          Forward a Day</a>";
    }
    if ($config->{nickmethod} &&
	$config->{nickmethod} eq 'drop') {
	print " | Select your nick: ";
	# Add dropdown box.	
	print "<form action=\"$config->{scriptname}\">";
       	print "<td><select class=\"nickdrop\" name=\"nick\" onchange='this.form.submit();'>";
	print "<option value=\"\">-------------</option>";
	my $nicks = YAML::LoadFile($config->{nickfile});
	foreach my $user (keys %$nicks) {
	    print "<option value=\"$user\" ";
	    if (param('nick')) {
		if ($user eq param('nick')) {
		    print "selected=\"selected\" ";
		}
	    }
	    print ">$user</option>";
	}
	print "</select>";
	if ($params =~ /r=t/) {
	    print "<input type=\"hidden\" name=\"r\" value=\"t\">";
	}
	if ($date ne todaysdate()) {
	    print "<input type=\"hidden\" name=\"l\" value=\"$date\">";
	}
	print "<noscript><input type=\"submit\" value=\"Submit\"></noscript>";
	print "</form>";
    }
    print "</td></tr></table>";
}

sub getParams {
    my $p = '?';
    my $r = '?';
    
    if (param('r')) {
	$p .= 'r=t&';
    } else {
	$r .= 'r=t&';
    }
    if (param('nick')) {
	$p .= "nick=" . param('nick') . "\&";
	$r .= "nick=" . param('nick') . "\&";
    }
    return ($p, $r);
}

sub PrintHead {		      
    my $l = shift;
    print qq(<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">);
    print "<head><title>";
    my $title = '#' . $config->{channame} . " Log for " . 
	substr($l,4,2) . "." . 
	substr($l,6,2) . "." . 
	substr($l,0,4);
    print $title . "</title>\n";
    # Check for custom CSS, else use default 'skin'
    if ($config->{cssfile}) {
	print "<link rel=\"stylesheet\" href=\"$config->{cssfile}\" type=\"text/css\">";
    } else {
	GetCSS();
    }
    print "<script src=\"" . $config->{jsroot} . "prototype.js\" type=\"text/javascript\"></script>\n";
    print "<script src=\"" . $config->{jsroot} . "scriptaculous.js\" type=\"text/javascript\"></script>\n";
    print "<script src=\"" . $config->{jsroot} . "unittest.js\" type=\"text/javascript\"></script>\n";
    print "<script>var myQuotes=new Array()</script>\n";
    print "</head><body>\n"; 
   
    # If you get no date Param, assume viewing live, and refresh every 5 mins.
    my @ps = getParams();
    my $refresh;
    if ($config->{refreshtime}) {
	$refresh = $config->{refreshtime};
    } else {
	$refresh = '300';
    }
    if ($l eq todaysdate()) {
	print "<meta http-equiv=\"Refresh\" content=\"$refresh;url=$config->{scriptname}$ps[0]\">";
    }

    print "<h2>$title</h2>\n";
}
sub PrintFoot {
    print "<p class=\"foot\">Version $ver, written by Brian.</p>";    
    print "</body></html>";
}
sub todaysdate {
    return substr(ParseDate("today"), 0, 8);
}
sub GetCSS {
    # Print CSS.
    print qq (
	      <style type="text/css">
	      body {
		  font-family: Monospace;
		  background-color: \#808080;
	      }
	      p.foot {
		  text-align: center;
		  font-size: small;
	      }
	      p.log {
		border: 1px solid black;
		  background-color: #A0A0A0;
		padding: 4px;
	      }
	      span.date {
		color: #404040;
	      }
	      span.brac {
		color: #062898
	      }
	      span.hl {
		background-color: #FFFF00;
	        padding: 2px;
	      }
	      span.nick {
		color: #800000;
	      }
	      a {
		color: #0000C0;
		text-decoration: none;
	      }
	      a:visited  { 
		color: #000040;
		text-decoration: none;
	      }
	      a:active {
	        color: #800000;
		text-decoration: none;
   	      }
	      a:hover {
		text-decoration: underline;
	        color: #800000;
	      }
              #menu {
                width: 300px;
                border: 1px #000 solid;
              }
              .menu_header {

              }
              .menu_block {
                overflow:hidden;
              }
              .menu_block div {
              }
              .close_block {
		position: relative;
                width: 100%;
                bottom: 0px;
                height: 15px;
                text-align: center;
                display: block;
              }
              .qbbox {
		border: 1px solid black;
	      }
              textarea.quotebox { 
		width: 95%;
		border: 1px solid black;
	      }
              input.submitbutton {
		border: 1px solid black;
		padding: 2px;
		background-color:  #808080;
	      }
              .nickdrop {
	        border: 1px solid black;
	      }
 	      </style>
	      );
}		
    
# Functions for Fortune file support. 
  
sub PrintQB {
    # Print a form with a large text area that allows for users to drop 
    # quotable  lines from the logs, and add them to the hard copy quote file.
    my $log = shift;
    print qq(
       <div class="menu_header" id="menu_header1"><a href="#" 
	  onClick="new Effect.SlideDown('menu_block1'); 
          return false;">Open Quote Pane</a>.</div>
       <div class="menu_block_container" id="menu_block_container1">
       <div style="display:none;" class="menu_block" id="menu_block1"><div>
       <div id="qb" class="qbbox" 
          style="text-align:center;padding:10px;background-color:#A0A0A0">
	     Drop Quotes Below
       <form method="GET" action="$config->{scriptname}"><br/>
       <textarea rows="6" name="q" class="quotebox" id="QuoteBox"></textarea>);
    
    # Snag the date to make sure we add to the right file.
    my $t = substr($log,0,4);
    print "<input name=\"y\" value=\"$t\" type=\"hidden\">";
    $t = substr($log,4,2);
    $t =~ s/^0//;
    print "<input name=\"m\" value=\"$t\" type=\"hidden\"><br/><br/>";
    print qq(<input type="submit" class="submitbutton" value="Add Quote">
      </form></div>
      <script type="text/javascript">
        Droppables.add('qb', {
	  onDrop:function(element,dropon){
	    var nl = '\\n';
	    var exLines = document.getElementById("QuoteBox").value;
	    document.getElementById("QuoteBox").value=exLines + element.id + nl;
	  }
        })
      </script>
      <a href="#" class="close_block" 
         onClick="new Effect.SlideUp('menu_block1'); return false;">Close</a>
      </div></div></div>);
}

sub PrintQuoteAdd {
    # Set up the quote adding variables.
    my $quote = shift;   
    my $year = shift;
    $year =~ s/^(20\d\d)$/$1/;
    my $month = shift;
    $month =~ s/^(\d\d)$/$1/;
    my @months = ('', 'January', 'February', 'March', 'April', 'May', 'June',
		  'July', 'August', 'September', 'October', 'November',
		  'December');
    my $qfilename;
    if ($config->{ffroot} && $year =~ /(20\d\d)/) {
	$qfilename = $config->{ffroot} . $1 . '_quotes.ff';
    } 

    $quote =~ s/\n$//;

    # Output HTML confirmation or error message.
    # print "Content-type: text/html\n\n";
    print qq(<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
	  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
	  <html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">);
    print "<head><title>Add Quote</title>";
    if ($config->{refreshtime}) {
	print "<meta http-equiv=\"Refresh\" content=\"$config->{refreshtime};url=$config->{scriptname}\">";
    } else {
	print "<meta http-equiv=\"Refresh\" content=\"5;url=$config->{scriptname}\">";
    }
    if ($config->{cssfile}) {
	print "<link rel=\"stylesheet\" href=\"$config->{cssfile}\" type=\"text/css\">";
    } else {
	GetCSS();
    }
    print "</head><body>";
    print "<h2>Add a New Quote</h2>";

    # Open the quote file, and append the qute to the end of the file.
    open(QFILE, ">>$qfilename") || 
	print "<p class=\"log\">Could not add quote, $qfilename was unable to be opened.</p>";
    print QFILE $quote . "\n\[$months[$month] $year\]" . "\n%\n";
    close(QFILE);
    
    print "<h3>Successfully Added:</h3><p class=\"log\">";

    # Do some rudimentary parsing. 
    $quote =~ s/</\&lt\;/g;
    $quote =~ s/>/\&gt\;/g;
    $quote =~ s/\n/<br\/>/g;

    print $quote . "<br/>\[$months[$month] $year\]";
    print "</p>";
    print "<h3>Redirecting back to todays' log in 5 seconds...</h3>";
}


